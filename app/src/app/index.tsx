import { Redirect } from 'expo-router';

/** Keep the root URL stable after moving the Home tab to ``/home``. */
export default function RootIndex() {
  // Expo refreshes generated route types when its dev server starts. The cast
  // also keeps standalone TypeScript checks working with a stale local cache.
  return <Redirect href={'/(tabs)/home' as any} />;
}
