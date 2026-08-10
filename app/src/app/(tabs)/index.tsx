import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

export default function HomeScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Image source={require('@/assets/images/partial-react-logo.png')} style={styles.reactLogo} />
      <View style={styles.titleContainer}>
        <Text style={styles.title}>Welcome to Emi Mower</Text>
      </View>
      <View style={styles.stepContainer}>
        <Text style={styles.subtitle}>Manage your mower fleet</Text>
        <Text>
          Use {Platform.select({ ios: 'cmd + d', android: 'cmd + m' })} to open developer tools
          while working on the app.
        </Text>
      </View>
      <View style={styles.stepContainer}>
        <Text style={styles.subtitle}>Operate your mower</Text>
        <Text>Use Controller for mower operations and Settings for your account.</Text>
      </View>
      <Link href="/(tabs)/settings" style={styles.link}>
        Open settings
      </Link>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, gap: 24 },
  titleContainer: { alignItems: 'center' },
  title: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 20, fontWeight: '600', marginBottom: 8 },
  stepContainer: { gap: 8 },
  link: { color: '#0a7ea4', fontWeight: '600' },
  reactLogo: { height: 140, width: 230, alignSelf: 'center' },
});
