import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, Modal, Portal, Text, TextInput } from 'react-native-paper';
import type { OwnershipResult } from '@/hooks/mowers/useMowerOwnership';

interface AddMowerModalProps {
  visible: boolean;
  onDismiss: () => void;
  onAddMower: (uuid: string) => Promise<OwnershipResult>;
  isPending: boolean;
}

export function AddMowerModal({ visible, onDismiss, onAddMower, isPending }: AddMowerModalProps) {
  const [uuid, setUuid] = useState('');
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (visible) {
      setUuid('');
      setError(undefined);
    }
  }, [visible]);

  const submit = async () => {
    setError(undefined);
    const result = await onAddMower(uuid);
    if (!result.success) {
      setError(result.error);
      return;
    }
    onDismiss();
  };

  return (
    <Portal>
      <Modal
        visible={visible}
        dismissable={!isPending}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modal}
      >
        <Text variant="titleLarge" style={styles.title}>
          Add mower
        </Text>
        <Text variant="bodyMedium" style={styles.description}>
          Enter the UUID printed on a registered, unassigned mower.
        </Text>
        <TextInput
          mode="outlined"
          label="Mower UUID"
          value={uuid}
          editable={!isPending}
          onChangeText={setUuid}
          autoCapitalize="none"
          error={Boolean(error)}
          textColor="#000000"
          style={styles.input}
          outlineColor="#6B7280"
          activeOutlineColor="#4CAF50"
          testID="add-mower-uuid"
        />
        <HelperText type="error" visible={Boolean(error)}>
          {error ?? ''}
        </HelperText>
        <View style={styles.actions}>
          <Button disabled={isPending} onPress={onDismiss}>
            Cancel
          </Button>
          <Button
            mode="contained"
            disabled={isPending}
            loading={isPending}
            onPress={submit}
            testID="confirm-add-mower"
          >
            {isPending ? 'Adding mower…' : 'Add mower'}
          </Button>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 6 },
  description: { color: '#D1D5DB', marginBottom: 14 },
  input: { backgroundColor: '#FFFFFF' },
  modal: { backgroundColor: '#1E1E1E', borderRadius: 18, margin: 24, padding: 20 },
  title: { color: '#FFFFFF', fontWeight: '700', marginBottom: 6 },
});
