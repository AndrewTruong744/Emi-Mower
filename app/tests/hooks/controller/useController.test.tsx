import { describe, expect, it, jest } from '@jest/globals';
import { act, renderHook } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { useController } from '@/hooks/controller/useController';
import { __mockGesture } from '../../mocks/gesture-handler';

describe('useController', () => {
  it('keeps configuration state together and emergency stop turns off power', () => {
    const alert = jest.spyOn(Alert, 'alert').mockImplementation(jest.fn());
    const { result } = renderHook(() => useController());

    act(() => result.current.handlePower());
    expect(result.current.currentConfig.power).toBe(true);

    act(() => result.current.handleEStop());
    expect(alert).toHaveBeenCalledWith('EMERGENCY STOP', expect.any(String), [{ text: 'OK' }]);
    expect(result.current.currentConfig).toMatchObject({ estop: true, power: false });

    act(() => result.current.handleEStop());
    expect(result.current.currentConfig.estop).toBe(false);
    alert.mockRestore();
  });

  it('keeps the configured state while updating a control', () => {
    const { result } = renderHook(() => useController());
    act(() => result.current.handlePower());

    expect(result.current.currentConfig.power).toBe(true);
  });

  it('forwards normalized joystick coordinates to the supplied command handler', () => {
    const onMove = jest.fn();
    renderHook(() => useController({ onMove }));

    (__mockGesture.updateCallback as unknown as (event: { translationX: number; translationY: number }) => void)({
      translationX: 100,
      translationY: -100,
    });
    (__mockGesture.endCallback as unknown as () => void)();

    expect(onMove).toHaveBeenCalledWith({
      x: expect.closeTo(Math.SQRT1_2),
      y: expect.closeTo(Math.SQRT1_2),
    });
    expect(onMove).toHaveBeenLastCalledWith({ x: 0, y: 0 });
  });
});
