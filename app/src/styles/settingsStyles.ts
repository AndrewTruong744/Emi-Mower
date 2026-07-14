import { StyleSheet } from 'react-native';

export const settingsStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212', // Premium deep dark background
    padding: 20,
  },
  scrollContainer: {
    paddingBottom: 40,
  },
  headerCard: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  avatar: {
    backgroundColor: '#4CAF50',
    marginBottom: 16,
  },
  userNameTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  userEmailSubtitle: {
    fontSize: 14,
    color: '#B0B0B0',
    marginTop: 4,
  },
  formCard: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  input: {
    backgroundColor: '#2C2C2C',
    marginBottom: 4,
  },
  inputDisabled: {
    backgroundColor: '#202020',
    marginBottom: 16,
  },
  helperText: {
    marginBottom: 12,
  },
  button: {
    borderRadius: 8,
    marginTop: 8,
    marginBottom: 16,
    paddingVertical: 4,
  },
  updateButton: {
    backgroundColor: '#4CAF50',
  },
  emailButton: {
    borderColor: '#4CAF50',
  },
  logoutButton: {
    backgroundColor: '#D32F2F',
    marginTop: 10,
  },
  buttonLabel: {
    fontWeight: 'bold',
    fontSize: 15,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(18, 18, 18, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 16,
    zIndex: 10,
  },
});
