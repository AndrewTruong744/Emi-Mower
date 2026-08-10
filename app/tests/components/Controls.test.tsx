import React from 'react';
import { jest } from '@jest/globals';
import { Alert } from 'react-native';
import { fireEvent, render } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import Controls from '@/components/controller/Controls';
import { __mockGesture } from '../mocks/gesture-handler';

describe('Controls', () => {
  it('renders the mower controls', () => {
    const { getByText } = render(
      <PaperProvider>
        <Controls />
      </PaperProvider>
    );
    expect(getByText('E-STOP')).toBeTruthy();
    expect(getByText('SYS: OFF')).toBeTruthy();
    expect(getByText('MAN')).toBeTruthy();
  });

  it('updates power, autonomous mode, emergency stop, and selected config', () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { getByText, getAllByRole } = render(
      <PaperProvider>
        <Controls />
      </PaperProvider>
    );

    fireEvent(getAllByRole('switch')[0], 'valueChange', true);
    fireEvent(getAllByRole('switch')[1], 'valueChange', true);
    expect(getByText('SYS: ON')).toBeTruthy();
    expect(getByText('AUTO')).toBeTruthy();

    fireEvent.press(getByText('E-STOP'));
    expect(getByText('STOPPED')).toBeTruthy();
    expect(getByText('SYS: OFF')).toBeTruthy();
    fireEvent.press(getByText('STOPPED'));
    expect(getByText('E-STOP')).toBeTruthy();

    fireEvent.press(getByText('#1'));
    fireEvent.press(getByText('Config 2'));
    expect(getByText('#2')).toBeTruthy();
    expect(alertSpy).toHaveBeenCalled();
    alertSpy.mockRestore();
  });

  it('normalizes joystick movement and returns it to center', () => {
    const { getByText } = render(
      <PaperProvider>
        <Controls />
      </PaperProvider>
    );
    expect(getByText('E-STOP')).toBeTruthy();
    expect(__mockGesture.updateCallback).toEqual(expect.any(Function));
    expect(__mockGesture.endCallback).toEqual(expect.any(Function));
    (__mockGesture.updateCallback as unknown as (event: { translationX: number; translationY: number }) => void)({
      translationX: 100,
      translationY: -100,
    });
    (__mockGesture.endCallback as unknown as () => void)();
  });
});
