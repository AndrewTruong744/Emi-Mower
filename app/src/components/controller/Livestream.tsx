import { StyleSheet, View } from 'react-native';
import { Button, Chip, Surface, Text } from 'react-native-paper';
import { useLivestream } from '@/hooks/controller/useLivestream';

interface LivestreamProps {
  mowerId: string | null;
}

/** Renders the selected mower's LiveKit connection controls. */
export function Livestream({ mowerId }: LivestreamProps) {
  const { connect, disconnect, isConnected, isPending } = useLivestream(mowerId);

  return (
    <Surface elevation={1} style={styles.card} testID="livestream-card">
      <View style={styles.frame}>
        <View style={styles.header}>
          <View>
            <Text variant="titleMedium" style={styles.title}>
              Livestream
            </Text>
          </View>
          <Chip icon={isConnected ? 'video' : 'video-off'}>
            {isConnected ? 'Connected' : 'Offline'}
          </Chip>
        </View>

        <View style={styles.preview} testID={isConnected ? 'livestream-preview' : undefined}>
          {isConnected ? (
            <>
              <Text variant="titleSmall" style={styles.previewTitle}>
                Live viewer connected
              </Text>
              <Text variant="bodySmall" style={styles.previewText}>
                Secure viewer credentials are active. Attach the native LiveKit video renderer to this
                connection.
              </Text>
            </>
          ) : null}

          <Button
            mode={isConnected ? 'outlined' : 'contained'}
            disabled={!mowerId || isPending}
            loading={isPending}
            onPress={isConnected ? disconnect : connect}
            testID="livestream-toggle"
          >
            {isConnected ? 'Disconnect stream' : 'Connect stream'}
          </Button>
        </View>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  card: { alignSelf: 'center', aspectRatio: 16 / 9, borderRadius: 16, marginBottom: 16, width: '100%' },
  frame: { backgroundColor: '#0f172a', borderRadius: 16, flex: 1, overflow: 'hidden' },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  preview: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  previewText: { color: '#cbd5e1', marginBottom: 16, marginTop: 6, textAlign: 'center' },
  previewTitle: { color: '#ffffff', fontWeight: '700' },
  title: { color: '#ffffff', fontWeight: '700' },
});
