import { StyleSheet, View } from 'react-native';
import { Button, Modal, Portal, Text } from 'react-native-paper';

interface ConfirmCuttingAreaModalProps {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmCuttingAreaModal({ visible, onCancel, onConfirm }: ConfirmCuttingAreaModalProps) {
  return (
    <Portal>
      <Modal visible={visible} onDismiss={onCancel} contentContainerStyle={styles.modal}>
        <Text variant="titleLarge" style={styles.title}>
          Start cutting session?
        </Text>
        <Text style={styles.description}>
          The selected boundary will lock the map while the mower fleet cuts this area.
        </Text>
        <View style={styles.actions}>
          <Button onPress={onCancel}>Cancel</Button>
          <Button mode="contained" onPress={onConfirm} testID="confirm-cutting-area">
            Confirm area
          </Button>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 12 },
  description: { color: '#D1D5DB' },
  modal: { backgroundColor: '#1E1E1E', borderRadius: 16, margin: 24, padding: 20 },
  title: { color: '#FFFFFF', fontWeight: '700', marginBottom: 8 },
});
