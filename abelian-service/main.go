package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/cloudflare/circl/sign/dilithium/mode3"
)

// Uses CRYSTALS-Dilithium Mode3 — the same NIST post-quantum signature
// standard used by the Abelian blockchain for quantum-resistant keys.

type GenerateResponse struct {
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

func handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	pub, priv, err := mode3.GenerateKey(rand.Reader)
	if err != nil {
		http.Error(w, fmt.Sprintf("key generation failed: %v", err), http.StatusInternalServerError)
		return
	}

	pubBytes, _ := pub.MarshalBinary()
	privBytes, _ := priv.MarshalBinary()

	resp := GenerateResponse{
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
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/keys/generate", handleGenerate)
	mux.HandleFunc("/sign", handleSign)
	mux.HandleFunc("/verify", handleVerify)
	mux.HandleFunc("/health", handleHealth)

	log.Println("Abelian crypto service starting on :8001")
	log.Println("Algorithm: CRYSTALS-Dilithium Mode3 (NIST PQC Standard)")
	if err := http.ListenAndServe(":8001", mux); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
