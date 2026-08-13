import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, Modal, Portal, Text, TextInput } from 'react-native-paper';

interface AddMowerModalProps {
  visible: boolean;
  onDismiss: () => void;
  onAddMower: (uuid: string) => { success: boolean; error?: string };
}

export function AddMowerModal({ visible, onDismiss, onAddMower }: AddMowerModalProps) {
  const [uuid, setUuid] = useState('');
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (visible) {
      setUuid('');
      setError(undefined);
    }
  }, [visible]);

  const submit = () => {
    const result = onAddMower(uuid);
    if (!result.success) {
      setError(result.error);
      return;
    }
    onDismiss();
  };

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onDismiss} contentContainerStyle={styles.modal}>
        <Text variant="titleLarge" style={styles.title}>
          Add mower
        </Text>
        <Text variant="bodyMedium" style={styles.description}>
          Enter the UUID printed on the mower. Connection will be added when the API hook is ready.
        </Text>
        <TextInput
          mode="outlined"
          label="Mower UUID"
          value={uuid}
          onChangeText={setUuid}
          autoCapitalize="none"
          error={Boolean(error)}
          textColor="#FFFFFF"
          outlineColor="#6B7280"
          activeOutlineColor="#4CAF50"
          testID="add-mower-uuid"
        />
        <HelperText type="error" visible={Boolean(error)}>
          {error ?? ''}
        </HelperText>
        <View style={styles.actions}>
          <Button onPress={onDismiss}>Cancel</Button>
          <Button mode="contained" onPress={submit} testID="confirm-add-mower">
            Add mower
          </Button>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 6 },
  description: { color: '#D1D5DB', marginBottom: 14 },
  modal: { backgroundColor: '#1E1E1E', borderRadius: 18, margin: 24, padding: 20 },
  title: { color: '#FFFFFF', fontWeight: '700', marginBottom: 6 },
});
