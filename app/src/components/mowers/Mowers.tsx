import { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Surface, Text } from 'react-native-paper';
import { useBoundStore } from '@/store/useBoundStore';
import { AddMowerModal } from './AddMowerModal';
import { MowerDetailsContent } from './MowerDetailsContent';
import { MowerSelector } from './MowerSelector';
import { RenameMowerModal } from './RenameMowerModal';
import { useMowerOwnership, type OwnershipResult } from '@/hooks/mowers/useMowerOwnership';
import { MowerOwnershipModal, type OwnershipSelection } from './MowerOwnershipModal';

export function Mowers() {
  const [isAddModalVisible, setAddModalVisible] = useState(false);
  const [isRenameModalVisible, setRenameModalVisible] = useState(false);
  const mowerIds = useBoundStore((state) => state.mowers);
  const selectedMowerUuid = useBoundStore((state) => state.selectedMowerUuid);
  const ownership = useMowerOwnership();
  const [ownershipSelection, setOwnershipSelection] = useState<OwnershipSelection | null>(null);
  const [feedback, setFeedback] = useState<OwnershipResult | null>(null);
  const renameMowerInStore = useBoundStore((state) => state.renameMower);
  const selectMower = useBoundStore((state) => state.selectMower);
  // Only read the name while its form is visible; telemetry updates must not
  // cause the surrounding page and selector to render.
  const activeMowerName = useBoundStore((state) =>
    isRenameModalVisible && selectedMowerUuid
      ? (state.mowerDetails[selectedMowerUuid]?.name ?? '')
      : ''
  );

  const showOwnership = (action: OwnershipSelection['action']) => {
    if (!selectedMowerUuid) return;
    const name =
      useBoundStore.getState().mowerDetails[selectedMowerUuid]?.name ?? selectedMowerUuid;
    setFeedback(null);
    setOwnershipSelection({ action, mowerId: selectedMowerUuid, name });
  };

  const renameActiveMower = useCallback(
    (name: string) => {
      const trimmedName = name.trim();
      if (!selectedMowerUuid) return { success: false, error: 'Select a mower first.' };
      if (!trimmedName) return { success: false, error: 'A mower name is required.' };

      renameMowerInStore(selectedMowerUuid, trimmedName);
      return { success: true };
    },
    [renameMowerInStore, selectedMowerUuid]
  );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={styles.heading}>
            <Text variant="headlineMedium" style={styles.title}>
              Mowers
            </Text>
            <Text variant="bodyMedium" style={styles.subtitle}>
              Monitor your mower fleet and its active session.
            </Text>
          </View>
          <Button
            mode="outlined"
            icon="refresh"
            disabled={ownership.isPending}
            onPress={async () => setFeedback(await ownership.refreshFleet())}
          >
            Refresh fleet
          </Button>
          <Button
            mode="contained"
            icon="plus"
            disabled={ownership.isPending}
            onPress={() => {
              setFeedback(null);
              setAddModalVisible(true);
            }}
            style={styles.addButton}
          >
            Add mower
          </Button>
        </View>

        {feedback && (
          <Text accessibilityLiveRegion="polite" style={styles.feedback}>
            {feedback.success ? feedback.message : feedback.error}
          </Text>
        )}

        <MowerSelector
          mowerIds={mowerIds}
          selectedMowerUuid={selectedMowerUuid}
          onSelect={selectMower}
        />

        {selectedMowerUuid && (
          <View style={styles.ownershipActions}>
            <Button
              mode="outlined"
              disabled={ownership.isPending}
              onPress={() => showOwnership('transfer')}
              testID="transfer-mower"
            >
              Transfer mower
            </Button>
            <Button
              mode="outlined"
              textColor="#ba1a1a"
              disabled={ownership.isPending}
              onPress={() => showOwnership('remove')}
              testID="remove-mower"
            >
              Remove mower
            </Button>
          </View>
        )}

        {mowerIds.length === 0 ? (
          <Surface elevation={1} style={styles.emptyState}>
            <Text variant="titleMedium" style={styles.emptyStateTitle}>
              No mowers in your fleet
            </Text>
            <Text variant="bodyMedium" style={styles.emptyStateMessage}>
              Add a mower to view its status, location, and telemetry.
            </Text>
          </Surface>
        ) : (
          <MowerDetailsContent
            mowerId={selectedMowerUuid}
            onEditName={() => setRenameModalVisible(true)}
          />
        )}
      </ScrollView>

      <AddMowerModal
        visible={isAddModalVisible}
        onDismiss={() => setAddModalVisible(false)}
        isPending={ownership.isPending}
        onAddMower={async (id) => {
          const result = await ownership.addMower(id);
          if (result.success) setFeedback(result);
          return result;
        }}
      />
      <MowerOwnershipModal
        selection={ownershipSelection}
        isPending={ownership.isPending}
        onDismiss={() => setOwnershipSelection(null)}
        onConfirm={async (selection, recipient) => {
          const result =
            selection.action === 'remove'
              ? await ownership.removeMower(selection.mowerId)
              : await ownership.transferMower(selection.mowerId, recipient);
          if (result.success) setFeedback(result);
          return result;
        }}
      />
      <RenameMowerModal
        visible={isRenameModalVisible}
        currentName={activeMowerName}
        onDismiss={() => setRenameModalVisible(false)}
        onRename={renameActiveMower}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  addButton: { alignSelf: 'flex-start', marginTop: 14 },
  feedback: { marginBottom: 16 },
  ownershipActions: { gap: 8, marginTop: 12 },
  emptyState: { borderRadius: 16, padding: 20 },
  emptyStateMessage: { marginTop: 6, opacity: 0.65 },
  emptyStateTitle: { fontWeight: '700' },
  header: { marginBottom: 20 },
  heading: { flexShrink: 1 },
  scrollContent: { padding: 20, paddingBottom: 36 },
  subtitle: { marginTop: 4, opacity: 0.65, paddingRight: 12 },
  title: { fontWeight: '700' },
});
