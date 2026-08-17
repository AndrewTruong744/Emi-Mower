import { memo } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Chip, Text } from 'react-native-paper';
import { useBoundStore } from '@/store/useBoundStore';

interface MowerSelectorProps {
  mowerIds: string[];
  selectedMowerUuid: string | null;
  onSelect: (uuid: string) => void;
}

/**
 * Each chip observes only its name. Live telemetry updates therefore do not
 * rebuild the selector or interrupt a mower change.
 */
export function MowerSelector({ mowerIds, selectedMowerUuid, onSelect }: MowerSelectorProps) {
  return (
    <View style={styles.container}>
      <Text variant="titleMedium" style={styles.title}>
        Displaying mower
      </Text>
      {mowerIds.length === 0 ? (
        <Text variant="bodyMedium" style={styles.emptyMessage}>
          No mowers have been added yet.
        </Text>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.list}>
          {mowerIds.map((mowerId) => (
            <MowerSelectorChip
              key={mowerId}
              mowerId={mowerId}
              selected={mowerId === selectedMowerUuid}
              onSelect={onSelect}
            />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

interface MowerSelectorChipProps {
  mowerId: string;
  selected: boolean;
  onSelect: (uuid: string) => void;
}

const MowerSelectorChip = memo(function MowerSelectorChip({
  mowerId,
  selected,
  onSelect,
}: MowerSelectorChipProps) {
  const mowerName = useBoundStore((state) => state.mowerDetails[mowerId]?.name ?? mowerId);

  return (
    <Chip
      selected={selected}
      onPress={() => onSelect(mowerId)}
      style={styles.chip}
      testID={`mower-selector-${mowerId}`}
    >
      {mowerName}
    </Chip>
  );
});

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  emptyMessage: { opacity: 0.65 },
  title: { fontWeight: '700', marginBottom: 8 },
  list: { gap: 8, paddingRight: 16 },
  chip: { marginRight: 8 },
});
