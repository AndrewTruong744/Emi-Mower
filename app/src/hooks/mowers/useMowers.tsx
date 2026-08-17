import { useCallback, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';

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
  const addMowerToStore = useBoundStore((state) => state.addMower);
  const renameMowerInStore = useBoundStore((state) => state.renameMower);
  const selectMowerInStore = useBoundStore((state) => state.selectMower);

  const activeMower = useMemo<MowerOption | null>(
    () =>
      selectedMowerUuid
        ? { uuid: selectedMowerUuid, name: mowerNames[mowerIds.indexOf(selectedMowerUuid)] ?? selectedMowerUuid }
        : null,
    [mowerIds, mowerNames, selectedMowerUuid]
  );
  const mowerOptions = useMemo(
    () => mowerIds.map((uuid, index) => ({ uuid, name: mowerNames[index] ?? uuid })),
    [mowerIds, mowerNames]
  );

  const addMower = useCallback(
    (uuid: string) => {
      const normalizedUuid = uuid.trim();
      if (!normalizedUuid) return { success: false, error: 'A mower UUID is required.' };
      if (mowerIds.includes(normalizedUuid)) {
        selectMowerInStore(normalizedUuid);
        return { success: false, error: 'That mower is already in your fleet.' };
      }

      addMowerToStore(normalizedUuid);
      return { success: true };
    },
    [addMowerToStore, mowerIds, selectMowerInStore]
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
    addMower,
    mowerIds,
    mowerOptions,
    renameActiveMower,
    selectMower: selectMowerInStore,
    selectedMowerUuid,
  };
}
