import { ScrollView, StyleSheet, View } from 'react-native';
import { Chip, Text } from 'react-native-paper';
import { MowerDetails } from '@/store/types';

interface MowerSelectorProps {
  mowers: MowerDetails[];
  selectedMowerUuid: string | null;
  onSelect: (uuid: string) => void;
}

export function MowerSelector({ mowers, selectedMowerUuid, onSelect }: MowerSelectorProps) {
  return (
    <View style={styles.container}>
      <Text variant="titleMedium" style={styles.title}>
        Displaying mower
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.list}>
        {mowers.map((mower) => (
          <Chip
            key={mower.uuid}
            selected={mower.uuid === selectedMowerUuid}
            onPress={() => onSelect(mower.uuid)}
            style={styles.chip}
            testID={`mower-selector-${mower.uuid}`}
          >
            {mower.name}
          </Chip>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  title: { fontWeight: '700', marginBottom: 8 },
  list: { gap: 8, paddingRight: 16 },
  chip: { marginRight: 8 },
});
