import { useCallback, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';
import { useMowerOwnership } from './useMowerOwnership';

export interface MowerOption {
  uuid: string;
  name: string;
}

export function useMowers() {
  const mowerIds = useBoundStore((state) => state.mowers);
  const selectedMowerUuid = useBoundStore((state) => state.selectedMowerUuid);
  const mowerNames = useBoundStore(
    useShallow((state) => state.mowers.map((uuid) => state.mowerDetails[uuid]?.name ?? uuid))
  );
  const ownership = useMowerOwnership();
  const renameMowerInStore = useBoundStore((state) => state.renameMower);
  const selectMowerInStore = useBoundStore((state) => state.selectMower);

  const activeMower = useMemo<MowerOption | null>(
    () =>
      selectedMowerUuid
        ? {
            uuid: selectedMowerUuid,
            name: mowerNames[mowerIds.indexOf(selectedMowerUuid)] ?? selectedMowerUuid,
          }
        : null,
    [mowerIds, mowerNames, selectedMowerUuid]
  );
  const mowerOptions = useMemo(
    () => mowerIds.map((uuid, index) => ({ uuid, name: mowerNames[index] ?? uuid })),
    [mowerIds, mowerNames]
  );

  const renameActiveMower = useCallback(
    (name: string) => {
      const trimmedName = name.trim();
      if (!activeMower) return { success: false, error: 'Select a mower first.' };
      if (!trimmedName) return { success: false, error: 'A mower name is required.' };

      renameMowerInStore(activeMower.uuid, trimmedName);
      return { success: true };
    },
    [activeMower, renameMowerInStore]
  );

  return {
    activeMower,
    ...ownership,
    mowerIds,
    mowerOptions,
    renameActiveMower,
    selectMower: selectMowerInStore,
    selectedMowerUuid,
  };
}
