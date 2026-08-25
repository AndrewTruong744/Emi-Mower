import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import { Button, Modal, Portal, Snackbar, Surface, Text } from 'react-native-paper';
import { useBoundStore } from '@/store/useBoundStore';

const TOAST_DURATION_MS = 6_000;

/** Presents one queued operational error at a time above every app route. */
export function GlobalErrorHost() {
  const error = useBoundStore((state) => state.errorQueue[0]);
  const dismissError = useBoundStore((state) => state.dismissError);

  useEffect(() => {
    if (!error || error.presentation !== 'toast') return;
    const timeout = setTimeout(() => dismissError(error.id), TOAST_DURATION_MS);
    return () => clearTimeout(timeout);
  }, [dismissError, error]);

  if (!error || error.presentation === 'silent') return null;

  const message = error.count > 1 ? `${error.message} (${error.count} times)` : error.message;

  return (
    <Portal>
      {error.presentation === 'modal' ? (
        <Modal
          visible
          onDismiss={() => dismissError(error.id)}
          contentContainerStyle={styles.modal}
        >
          <Surface elevation={3} style={styles.surface}>
            <Text variant="titleLarge" style={styles.title}>{error.title}</Text>
            <Text style={styles.message}>{message}</Text>
            <Button mode="contained" onPress={() => dismissError(error.id)}>
              Dismiss
            </Button>
          </Surface>
        </Modal>
      ) : (
        <Snackbar visible onDismiss={() => dismissError(error.id)} duration={TOAST_DURATION_MS}>
          {error.title}: {message}
        </Snackbar>
      )}
    </Portal>
  );
}

const styles = StyleSheet.create({
  modal: { margin: 20 },
  surface: { borderRadius: 16, padding: 24 },
  title: { fontWeight: '700', marginBottom: 12 },
  message: { marginBottom: 24, opacity: 0.72 },
});
