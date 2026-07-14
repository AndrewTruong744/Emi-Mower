import { StyleSheet } from 'react-native';

export const loginStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212', // Premium deep dark background
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#1E1E1E', // Elevate surface dark card
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoIcon: {
    backgroundColor: '#4CAF50', // Vibrant lawn green brand color
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 5,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#B0B0B0',
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 22,
  },
  button: {
    width: '100%',
    borderRadius: 28,
    paddingVertical: 6,
    backgroundColor: '#FFFFFF', // Clean white background for Google button
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  buttonLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#000000',
  },
  loader: {
    marginTop: 20,
  },
  errorText: {
    color: '#FF5252',
    textAlign: 'center',
    marginTop: 16,
    fontSize: 14,
  },
  snackbar: {
    backgroundColor: '#D32F2F',
  },
});
