package main

// Abelian Quantum-Resistant Crypto Service
//
// Mnemonic algorithm ported from pqabelian/abelian-sdk-go (MIT License).
// Uses CRYSTALS-Dilithium Mode3 via cloudflare/circl.

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"

	"github.com/cloudflare/circl/sign/dilithium/mode3"
	"golang.org/x/crypto/sha3"
)

// ── Mnemonic (ported from pqabelian/abelian-sdk-go, MIT) ──────────────

const seedLength = 32

func doubleHash(b []byte) [32]byte {
	first := sha256.Sum256(b)
	return sha256.Sum256(first[:])
}

func seedToWords(seed []byte) []string {
	hash := doubleHash(seed)
	tmp := make([]byte, len(seed)+1)
	copy(tmp, seed)
	tmp[len(seed)] = hash[0]

	res := make([]string, 0, 24)
	for pos := 0; pos < len(tmp); pos += 11 {
		res = append(res,
			bip39English[(int(tmp[pos])<<3)|int(tmp[pos+1]>>5)],
			bip39English[(int(tmp[pos+1]&0x1F)<<6)|int(tmp[pos+2]>>2)],
			bip39English[(int(tmp[pos+2]&0x3)<<9)|(int(tmp[pos+3])<<1)|int(tmp[pos+4]>>7)],
			bip39English[(int(tmp[pos+4]&0x7F)<<4)|int(tmp[pos+5]>>4)],
			bip39English[(int(tmp[pos+5]&0xF)<<7)|int(tmp[pos+6]>>1)],
			bip39English[(int(tmp[pos+6]&0x1)<<10)|(int(tmp[pos+7])<<2)|int(tmp[pos+8]>>6)],
			bip39English[(int(tmp[pos+8]&0x3F)<<5)|int(tmp[pos+9]>>3)],
			bip39English[(int(tmp[pos+9]&0x7)<<8)|int(tmp[pos+10])],
		)
	}
	return res
}

func wordsToSeed(words []string) ([]byte, error) {
	if len(words) != 24 {
		return nil, fmt.Errorf("mnemonic must be exactly 24 words, got %d", len(words))
	}
	indices := make([]int, 24)
	for i, w := range words {
		w = strings.TrimSpace(strings.ToLower(w))
		idx, ok := bip39Map[w]
		if !ok {
			return nil, fmt.Errorf("unknown mnemonic word: %q", w)
		}
		indices[i] = idx
	}

	res := make([]byte, 0, seedLength+1)
	for pos := 0; pos < len(indices); pos += 8 {
		res = append(res,
			byte((indices[pos]&0x7F8)>>3),
			byte((indices[pos]&0x7)<<5)|byte((indices[pos+1]&0x7C0)>>6),
			byte((indices[pos+1]&0x3F)<<2)|byte((indices[pos+2]&0x600)>>9),
			byte((indices[pos+2]&0x1FE)>>1),
			byte((indices[pos+2]&0x1)<<7)|byte((indices[pos+3]&0x7F0)>>4),
			byte((indices[pos+3]&0xF)<<4)|byte((indices[pos+4]&0x780)>>7),
			byte((indices[pos+4]&0x7F)<<1)|byte((indices[pos+5]&0x400)>>10),
			byte((indices[pos+5]&0x3FC)>>2),
			byte((indices[pos+5]&0x3)<<6)|byte((indices[pos+6]&0x7E0)>>5),
			byte((indices[pos+6]&0x1F)<<3)|byte((indices[pos+7]&0x700)>>8),
			byte(indices[pos+7]&0xFF),
		)
	}

	seedH := doubleHash(res[:seedLength])
	if !bytes.Equal(seedH[:1], res[seedLength:]) {
		return nil, fmt.Errorf("invalid mnemonic checksum")
	}
	return res[:seedLength], nil
}

func generateRandomMnemonic() ([]string, error) {
	seed := make([]byte, seedLength)
	if _, err := rand.Read(seed); err != nil {
		return nil, err
	}
	return seedToWords(seed), nil
}

// seedToDilithiumReader expands a 32-byte seed into a deterministic
// io.Reader suitable for mode3.GenerateKey using SHAKE256.
func seedToDilithiumReader(seed []byte) io.Reader {
	h := sha3.NewShake256()
	h.Write([]byte("abelian-dilithium-keygen"))
	h.Write(seed)
	return h
}

func keysFromMnemonic(words []string) (*mode3.PublicKey, *mode3.PrivateKey, error) {
	seed, err := wordsToSeed(words)
	if err != nil {
		return nil, nil, err
	}
	reader := seedToDilithiumReader(seed)
	pub, priv, err := mode3.GenerateKey(reader)
	if err != nil {
		return nil, nil, fmt.Errorf("key generation failed: %w", err)
	}
	return pub, priv, nil
}

// ── HTTP types ────────────────────────────────────────────────────────

type GenerateResponse struct {
	CryptoAddress  string   `json:"crypto_address"`
	SpendSecretKey string   `json:"spend_secret_key"`
	PublicKeyHex   string   `json:"public_key_hex"`
	Mnemonic       []string `json:"mnemonic"`
}

type RestoreRequest struct {
	Mnemonic string `json:"mnemonic"`
}

type RestoreResponse struct {
	CryptoAddress  string `json:"crypto_address"`
	SpendSecretKey string `json:"spend_secret_key"`
	PublicKeyHex   string `json:"public_key_hex"`
}

type SignRequest struct {
	Message        string `json:"message"`
	SpendSecretKey string `json:"spend_secret_key"`
}

type SignResponse struct {
	Signature string `json:"signature"`
}

type VerifyRequest struct {
	Message       string `json:"message"`
	Signature     string `json:"signature"`
	CryptoAddress string `json:"crypto_address"`
}

type VerifyResponse struct {
	Valid bool `json:"valid"`
}

// ── Handlers ──────────────────────────────────────────────────────────

func handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	mnemonic, err := generateRandomMnemonic()
	if err != nil {
		http.Error(w, fmt.Sprintf("mnemonic generation failed: %v", err), http.StatusInternalServerError)
		return
	}

	pub, priv, err := keysFromMnemonic(mnemonic)
	if err != nil {
		http.Error(w, fmt.Sprintf("key derivation failed: %v", err), http.StatusInternalServerError)
		return
	}

	pubBytes, _ := pub.MarshalBinary()
	privBytes, _ := priv.MarshalBinary()

	resp := GenerateResponse{
		CryptoAddress:  hex.EncodeToString(pubBytes),
		SpendSecretKey: hex.EncodeToString(privBytes),
		PublicKeyHex:   hex.EncodeToString(pubBytes),
		Mnemonic:       mnemonic,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func handleRestore(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req RestoreRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	words := strings.Fields(strings.TrimSpace(req.Mnemonic))
	pub, priv, err := keysFromMnemonic(words)
	if err != nil {
		http.Error(w, fmt.Sprintf("restore failed: %v", err), http.StatusBadRequest)
		return
	}

	pubBytes, _ := pub.MarshalBinary()
	privBytes, _ := priv.MarshalBinary()

	resp := RestoreResponse{
		CryptoAddress:  hex.EncodeToString(pubBytes),
		SpendSecretKey: hex.EncodeToString(privBytes),
		PublicKeyHex:   hex.EncodeToString(pubBytes),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func handleSign(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req SignRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	privBytes, err := hex.DecodeString(req.SpendSecretKey)
	if err != nil {
		http.Error(w, "invalid spend_secret_key hex", http.StatusBadRequest)
		return
	}

	var priv mode3.PrivateKey
	if err := priv.UnmarshalBinary(privBytes); err != nil {
		http.Error(w, "invalid private key", http.StatusBadRequest)
		return
	}

	sig := make([]byte, mode3.SignatureSize)
	mode3.SignTo(&priv, []byte(req.Message), sig)

	resp := SignResponse{
		Signature: hex.EncodeToString(sig),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func handleVerify(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req VerifyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	pubBytes, err := hex.DecodeString(req.CryptoAddress)
	if err != nil {
		http.Error(w, "invalid crypto_address hex", http.StatusBadRequest)
		return
	}

	sigBytes, err := hex.DecodeString(req.Signature)
	if err != nil {
		http.Error(w, "invalid signature hex", http.StatusBadRequest)
		return
	}

	var pub mode3.PublicKey
	if err := pub.UnmarshalBinary(pubBytes); err != nil {
		http.Error(w, "invalid public key", http.StatusBadRequest)
		return
	}

	valid := mode3.Verify(&pub, []byte(req.Message), sigBytes)

	resp := VerifyResponse{Valid: valid}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":    "ok",
		"algorithm": "CRYSTALS-Dilithium Mode3 (NIST PQC Standard)",
		"mnemonic":  "BIP-39 compatible (ported from pqabelian/abelian-sdk-go)",
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/keys/generate", handleGenerate)
	mux.HandleFunc("/keys/restore", handleRestore)
	mux.HandleFunc("/sign", handleSign)
	mux.HandleFunc("/verify", handleVerify)
	mux.HandleFunc("/health", handleHealth)

	log.Println("Abelian crypto service starting on :8001")
	log.Println("Algorithm: CRYSTALS-Dilithium Mode3 (NIST PQC Standard)")
	log.Println("Mnemonic: BIP-39 compatible (ported from pqabelian/abelian-sdk-go)")
	if err := http.ListenAndServe(":8001", mux); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
