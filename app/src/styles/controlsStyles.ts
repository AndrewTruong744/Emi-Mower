import { StyleSheet } from 'react-native';

export const JOYSTICK_SIZE = 200;
export const controlsStyles = StyleSheet.create({
  controls: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bar: {
    flexDirection: 'row',
    width: '95%',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    padding: 8,
    borderRadius: 12,
    marginBottom: 20,
    gap: 8,
  },
  dropdownButton: {
    borderColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 8,
    minWidth: 0,
  },
  dropdownButtonLabel: {
    color: '#fff',
    fontSize: 13,
    marginHorizontal: 2,
    fontWeight: 'bold',
  },
  estopButton: {
    borderWidth: 2,
    borderRadius: 8,
  },
  estopInactive: {
    backgroundColor: '#dc2626',
    borderColor: '#b91c1c',
  },
  estopActive: {
    backgroundColor: '#991b1b',
    borderColor: '#450a0a',
  },
  estopLabel: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 13,
    letterSpacing: 0.5,
    marginVertical: 6,
  },
  toggleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  toggleLabel: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
  base: {
    width: JOYSTICK_SIZE,
    height: JOYSTICK_SIZE,
    borderRadius: JOYSTICK_SIZE / 2,
    backgroundColor: '#c8c8c8',
    borderWidth: 2,
    borderColor: '#ccc',
    justifyContent: 'center',
    alignItems: 'center',
  },
  knob: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#6200ee',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
});
