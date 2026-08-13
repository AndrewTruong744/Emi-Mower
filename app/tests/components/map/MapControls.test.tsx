import React from 'react';
import { describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';
import { BoundaryControls } from '@/components/map/BoundaryControls';
import { ConfirmCuttingAreaModal } from '@/components/map/ConfirmCuttingAreaModal';
import { MapSessionControls } from '@/components/map/MapSessionControls';
import { MapStyleSelector } from '@/components/map/MapStyleSelector';
import { PaperProvider } from 'react-native-paper';

describe('map controls', () => {
  it('clears a pending boundary and controls a mower session', () => {
    const onClear = jest.fn();
    const onAccept = jest.fn();
    const onPauseToggle = jest.fn();
    const onCancel = jest.fn();
    const screen = render(
      <PaperProvider>
        <BoundaryControls pointCount={3} onAccept={onAccept} onClear={onClear} />
        <MapSessionControls
          isPaused={false}
          mowerCount={2}
          onCancel={onCancel}
          onPauseToggle={onPauseToggle}
        />
      </PaperProvider>
    );

    fireEvent.press(screen.getByText('Clear boundary'));
    fireEvent.press(screen.getByTestId('accept-boundary'));
    fireEvent.press(screen.getByTestId('pause-mowing-session'));
    fireEvent.press(screen.getByTestId('cancel-mowing-session'));
    expect(StyleSheet.flatten(screen.getByTestId('boundary-actions').props.style)).toMatchObject({
      flexDirection: 'row',
      justifyContent: 'space-between',
    });
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(onPauseToggle).toHaveBeenCalledTimes(1);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('confirms or dismisses the cutting-area modal', () => {
    const onCancel = jest.fn();
    const onConfirm = jest.fn();
    const screen = render(
      <PaperProvider>
        <ConfirmCuttingAreaModal visible onCancel={onCancel} onConfirm={onConfirm} />
      </PaperProvider>
    );

    fireEvent.press(screen.getByText('Cancel'));
    fireEvent.press(screen.getByTestId('confirm-cutting-area'));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('switches between satellite and street map styles', () => {
    const onChange = jest.fn();
    const screen = render(
      <PaperProvider>
        <MapStyleSelector baseMap="satellite" onChange={onChange} />
      </PaperProvider>
    );

    fireEvent.press(screen.getByTestId('map-style-street'));
    fireEvent.press(screen.getByTestId('map-style-satellite'));
    expect(onChange).toHaveBeenNthCalledWith(1, 'street');
    expect(onChange).toHaveBeenNthCalledWith(2, 'satellite');
  });
});
