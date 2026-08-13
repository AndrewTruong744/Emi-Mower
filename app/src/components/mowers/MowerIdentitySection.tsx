import { StyleSheet, View } from 'react-native';
import { Button, Surface, Text } from 'react-native-paper';
import { MowerDetails } from '@/store/types';

interface MowerIdentitySectionProps {
  mower: MowerDetails;
  onEditName: () => void;
}

export function MowerIdentitySection({ mower, onEditName }: MowerIdentitySectionProps) {
  return (
    <Surface elevation={1} style={styles.card}>
      <View style={styles.heading}>
        <View>
          <Text variant="labelMedium" style={styles.label}>
            Mower name
          </Text>
          <Text variant="titleLarge" style={styles.name}>
            {mower.name}
          </Text>
        </View>
        <Button mode="outlined" onPress={onEditName} testID="edit-mower-name">
          Edit name
        </Button>
      </View>
      <Text variant="labelLarge" style={styles.label}>
        UUID
      </Text>
      <Text selectable style={styles.uuid}>
        {mower.uuid}
      </Text>
    </Surface>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 16, marginBottom: 16, padding: 16 },
  heading: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18 },
  label: { opacity: 0.65 },
  name: { fontWeight: '700' },
  uuid: { fontFamily: 'monospace', marginTop: 3 },
});
