import { Tabs } from "expo-router";
import { Text } from "react-native";
import { Colors } from "../../src/constants/theme";

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Courses: "📚",
    Profile: "👤",
  };
  return (
    <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.5 }}>
      {icons[name] || "📱"}
    </Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: Colors.background },
        headerTintColor: Colors.text,
        headerTitleStyle: { fontWeight: "700" },
        tabBarStyle: {
          backgroundColor: Colors.surface,
          borderTopColor: Colors.border,
          borderTopWidth: 1,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "My Courses",
          tabBarLabel: "Courses",
          tabBarIcon: ({ focused }) => (
            <TabIcon name="Courses" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ focused }) => (
            <TabIcon name="Profile" focused={focused} />
          ),
        }}
      />
    </Tabs>
  );
}
