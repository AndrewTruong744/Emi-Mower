import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, Modal, Portal, Text, TextInput } from 'react-native-paper';

interface RenameMowerModalProps {
  visible: boolean;
  currentName: string;
  onDismiss: () => void;
  onRename: (name: string) => { success: boolean; error?: string };
}

export function RenameMowerModal({ visible, currentName, onDismiss, onRename }: RenameMowerModalProps) {
  const [name, setName] = useState(currentName);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (visible) {
      setName(currentName);
      setError(undefined);
    }
  }, [currentName, visible]);

  const submit = () => {
    const result = onRename(name);
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
          Rename mower
        </Text>
        <TextInput
          mode="outlined"
          label="Mower name"
          value={name}
          onChangeText={setName}
          error={Boolean(error)}
          textColor="#FFFFFF"
          outlineColor="#6B7280"
          activeOutlineColor="#4CAF50"
          testID="rename-mower-name"
        />
        <HelperText type="error" visible={Boolean(error)}>
          {error ?? ''}
        </HelperText>
        <View style={styles.actions}>
          <Button onPress={onDismiss}>Cancel</Button>
          <Button mode="contained" onPress={submit} testID="confirm-rename-mower">
            Save name
          </Button>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 6 },
  modal: { backgroundColor: '#1E1E1E', borderRadius: 18, margin: 24, padding: 20 },
  title: { color: '#FFFFFF', fontWeight: '700', marginBottom: 14 },
});
