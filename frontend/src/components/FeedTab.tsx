import { useState, useCallback, useRef } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  ActivityIndicator,
  ViewToken,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { getFeed } from "../api/feed";
import { submitProgress } from "../api/progress";
import { FeedItem } from "../api/types";
import ReelCard from "./ReelCard";
import QuizCard from "./QuizCard";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const CARD_HEIGHT = SCREEN_HEIGHT - 200;

interface Props {
  courseId: number;
}

export default function FeedTab({ courseId }: Props) {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);

  const fetchFeed = useCallback(async () => {
    try {
      const data = await getFeed(courseId);
      setItems(data.items);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useFocusEffect(
    useCallback(() => {
      fetchFeed();
    }, [fetchFeed])
  );

  const onViewableItemsChanged = useRef(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (viewableItems.length > 0 && viewableItems[0].index != null) {
        setActiveIndex(viewableItems[0].index);
      }
    }
  ).current;

  const handleReelWatched = async (subtopicId: number | null) => {
    if (subtopicId) {
      try {
        await submitProgress(subtopicId, { reel_watched: true });
      } catch {}
    }
  };

  const handleQuizAnswer = async (
    quizItemId: number,
    subtopicId: number | null,
    answer: string
  ) => {
    if (!subtopicId) return null;
    try {
      const result = await submitProgress(subtopicId, {
        quiz_item_id: quizItemId,
        user_answer: answer,
      });
      return result;
    } catch {
      return null;
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (items.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyIcon}>🎬</Text>
        <Text style={styles.emptyTitle}>No content yet</Text>
        <Text style={styles.emptyDesc}>
          Upload materials and generate content to see your Focus Feed
        </Text>
      </View>
    );
  }

  const renderItem = ({ item, index }: { item: FeedItem; index: number }) => {
    if (item.type === "reel") {
      return (
        <View style={[styles.card, { height: CARD_HEIGHT }]}>
          <ReelCard
            reel={item.reel}
            isActive={index === activeIndex}
            onWatched={() => handleReelWatched(item.reel.subtopic_id)}
          />
        </View>
      );
    }
    return (
      <View style={[styles.card, { height: CARD_HEIGHT }]}>
        <QuizCard
          quiz={item.quiz}
          onAnswer={(answer) =>
            handleQuizAnswer(item.quiz.id, item.quiz.subtopic_id, answer)
          }
        />
      </View>
    );
  };

  return (
    <FlatList
      ref={flatListRef}
      data={items}
      renderItem={renderItem}
      keyExtractor={(item, idx) => {
        if (item.type === "reel") return `reel-${item.reel.id}`;
        return `quiz-${item.quiz.id}-${idx}`;
      }}
      pagingEnabled
      snapToInterval={CARD_HEIGHT}
      decelerationRate="fast"
      showsVerticalScrollIndicator={false}
      onViewableItemsChanged={onViewableItemsChanged}
      viewabilityConfig={{ itemVisiblePercentThreshold: 50 }}
      contentContainerStyle={styles.list}
    />
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.xl,
  },
  list: { paddingBottom: 20 },
  card: {
    marginHorizontal: Spacing.sm,
    marginVertical: Spacing.xs,
  },
  emptyIcon: { fontSize: 60, marginBottom: Spacing.md },
  emptyTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  emptyDesc: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    textAlign: "center",
  },
});
