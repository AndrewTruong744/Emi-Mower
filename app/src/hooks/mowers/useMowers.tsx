import { useCallback, useEffect, useMemo } from 'react';
import { useBoundStore } from '@/store/useBoundStore';
import { useMowerTelemetrySimulator } from './useMowerTelemetrySimulator';

export function useMowers() {
  const mowerIds = useBoundStore((state) => state.mowers);
  const mowerDetails = useBoundStore((state) => state.mowerDetails);
  const selectedMowerUuid = useBoundStore((state) => state.selectedMowerUuid);
  const seedFakeMowers = useBoundStore((state) => state.seedFakeMowers);
  const addMowerToStore = useBoundStore((state) => state.addMower);
  const renameMowerInStore = useBoundStore((state) => state.renameMower);
  const selectMowerInStore = useBoundStore((state) => state.selectMower);

  useEffect(() => {
    seedFakeMowers();
  }, [seedFakeMowers]);

  useMowerTelemetrySimulator();

  const activeMower = selectedMowerUuid ? mowerDetails[selectedMowerUuid] ?? null : null;
  const mowerOptions = useMemo(
    () => mowerIds.map((uuid) => mowerDetails[uuid]).filter(Boolean),
    [mowerDetails, mowerIds]
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
    mowerOptions,
    renameActiveMower,
    selectMower: selectMowerInStore,
    selectedMowerUuid,
  };
}
