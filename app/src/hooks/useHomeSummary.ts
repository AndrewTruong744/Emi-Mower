import { useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useBoundStore } from '@/store/useBoundStore';

export interface HomeSummaryItem {
  id: 'controller' | 'mowers' | 'map' | 'settings';
  title: string;
  description: string;
  href: '/(tabs)/controller' | '/(tabs)/mowers' | '/(tabs)/map' | '/(tabs)/settings';
  actionLabel: string;
  status: string;
}

/** Derives the dashboard's compact view of the other tabs from shared state. */
export function useHomeSummary() {
  const {
    displayName,
    email,
    isSessionActive,
    isSessionPaused,
    mowerDetails,
    mowers,
    selectedMowerUuid,
  } = useBoundStore(
    useShallow((state) => ({
      displayName: state.displayName,
      email: state.email,
      isSessionActive: state.isSessionActive,
      isSessionPaused: state.isSessionPaused,
      mowerDetails: state.mowerDetails,
      mowers: state.mowers,
      selectedMowerUuid: state.selectedMowerUuid,
    }))
  );

  return useMemo(() => {
    const activeMower = selectedMowerUuid ? mowerDetails[selectedMowerUuid] : null;
    const sessionStatus = isSessionActive
      ? isSessionPaused
        ? 'Session paused'
        : 'Session active'
      : 'No active session';

    const items: HomeSummaryItem[] = [
      {
        id: 'controller',
        title: 'Controller',
        description: 'Use manual controls, power, autonomy, and emergency stop.',
        href: '/(tabs)/controller',
        actionLabel: 'Open controller',
        status: isSessionActive ? 'Fleet available' : 'Ready when needed',
      },
      {
        id: 'mowers',
        title: 'Mowers',
        description: 'Review fleet health, live metrics, and historical graphs.',
        href: '/(tabs)/mowers',
        actionLabel: 'View mowers',
        status: activeMower
          ? `${mowers.length} mowers · ${activeMower.battery == null ? 'battery unavailable' : `${activeMower.battery.toFixed(0)}% battery`}`
          : `${mowers.length} mowers`,
      },
      {
        id: 'map',
        title: 'Map',
        description: 'Draw the cutting boundary and monitor the active session.',
        href: '/(tabs)/map',
        actionLabel: 'Open map',
        status: sessionStatus,
      },
      {
        id: 'settings',
        title: 'Settings',
        description: 'Manage your profile, email address, and sign-in session.',
        href: '/(tabs)/settings',
        actionLabel: 'Open settings',
        status: displayName || email || 'Account not configured',
      },
    ];

    return {
      activeMowerName: activeMower?.name ?? 'No mower selected',
      fleetCount: mowers.length,
      items,
      sessionStatus,
    };
  }, [
    displayName,
    email,
    isSessionActive,
    isSessionPaused,
    mowerDetails,
    mowers,
    selectedMowerUuid,
  ]);
}
