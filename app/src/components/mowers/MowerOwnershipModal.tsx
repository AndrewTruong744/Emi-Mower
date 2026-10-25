import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, HelperText, Modal, Portal, Text, TextInput } from 'react-native-paper';
import type { OwnershipResult } from '@/hooks/mowers/useMowerOwnership';

export interface OwnershipSelection {
  action: 'remove' | 'transfer';
  mowerId: string;
  name: string;
}

interface Props {
  selection: OwnershipSelection | null;
  isPending: boolean;
  onDismiss: () => void;
  onConfirm: (selection: OwnershipSelection, recipient: string) => Promise<OwnershipResult>;
}

export function MowerOwnershipModal({ selection, isPending, onDismiss, onConfirm }: Props) {
  const [recipient, setRecipient] = useState('');
  const [error, setError] = useState<string>();
  useEffect(() => {
    setRecipient('');
    setError(undefined);
  }, [selection]);
  const transfer = selection?.action === 'transfer';
  const submit = async () => {
    if (!selection) return;
    setError(undefined);
    const result = await onConfirm(selection, recipient);
    if (result.success) onDismiss();
    else setError(result.error);
  };
  return (
    <Portal>
      <Modal
        visible={Boolean(selection)}
        dismissable={!isPending}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modal}
      >
        <Text variant="titleLarge" style={styles.title}>
          {transfer ? 'Transfer mower' : 'Remove mower'}
        </Text>
        <Text style={styles.description}>
          {transfer
            ? `Transfer ${selection?.name ?? 'this mower'} and its access to another account. You will lose access to this mower.`
            : `Remove ${selection?.name ?? 'this mower'} from your account. It will become unassigned and can be added by another account. Its records and telemetry will be kept.`}
        </Text>
        {transfer && (
          <>
            <TextInput
              label="Recipient User ID (UID)"
              mode="outlined"
              value={recipient}
              onChangeText={setRecipient}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isPending}
              textColor="#000000"
              style={styles.input}
              error={Boolean(error)}
              testID="transfer-recipient-uid"
            />
            <Text style={styles.description}>
              Ask the recipient for the User ID shown in their Settings.
            </Text>
          </>
        )}
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
            testID="confirm-mower-ownership"
          >
            {isPending ? 'Updating…' : transfer ? 'Transfer mower' : 'Remove mower'}
          </Button>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  modal: { backgroundColor: '#1E1E1E', borderRadius: 18, margin: 24, padding: 20 },
  title: { color: '#FFFFFF', fontWeight: '700', marginBottom: 14 },
  description: { color: '#D1D5DB', marginBottom: 14 },
  input: { backgroundColor: '#FFFFFF', marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end' },
});
