import { Formik } from 'formik';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Avatar,
  Button,
  HelperText,
  Surface,
  Text,
  TextInput,
} from 'react-native-paper';
import { useSettings } from '@/hooks/settings/useSettings';

interface FormValues {
  displayName: string;
}

function validate(values: FormValues) {
  const errors: { displayName?: string } = {};
  if (!values.displayName) {
    errors.displayName = 'Name is required';
  } else if (!/^[a-zA-Z0-9_]+$/.test(values.displayName)) {
    errors.displayName = 'Name must be alphanumeric';
  } else if (values.displayName.length > 32) {
    errors.displayName = 'Name must be at most 32 characters';
  }
  return errors;
}

function getInitials(name: string | null) {
  if (!name) return 'U';
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .substring(0, 2);
}

/** Profile, account update, email, and sign-out UI for the Settings tab. */
export function Settings() {
  const {
    user,
    updateUsername,
    changeEmail,
    logout,
    isUpdatingUsername,
    isUpdatingEmail,
    isLoggingOut,
  } = useSettings();
  const showLoadingOverlay = isUpdatingUsername || isUpdatingEmail || isLoggingOut;

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.header}>
          <Text variant="headlineMedium" style={styles.pageTitle}>
            Settings
          </Text>
          <Text variant="bodyMedium" style={styles.pageSubtitle}>
            Manage your profile and sign-in session.
          </Text>
        </View>
        <Surface elevation={1} style={styles.headerCard}>
          <Avatar.Text
            size={80}
            label={getInitials(user.displayName)}
            style={styles.avatar}
            labelStyle={styles.avatarLabel}
          />
          <Text style={styles.userNameTitle}>{user.displayName || 'No Name Set'}</Text>
          <Text style={styles.userEmailSubtitle}>{user.email || 'No Email Set'}</Text>
        </Surface>

        <Surface elevation={1} style={styles.formCard}>
          <Text variant="titleMedium" style={styles.cardTitle}>
            Account settings
          </Text>
          <TextInput
            mode="outlined"
            label="User ID (UID)"
            value={user.user_id || ''}
            editable={false}
            disabled
            style={styles.inputDisabled}
          />
          <TextInput
            mode="outlined"
            label="Email Address"
            value={user.email || ''}
            editable={false}
            disabled
            style={styles.inputDisabled}
          />
          <Formik
            initialValues={{ displayName: user.displayName || '' }}
            enableReinitialize
            validate={validate}
            onSubmit={(values) => updateUsername(values.displayName)}
          >
            {({
              handleChange,
              handleBlur,
              handleSubmit,
              values,
              errors,
              touched,
              isValid,
              dirty,
            }) => (
              <View>
                <TextInput
                  mode="outlined"
                  label="Display Name"
                  value={values.displayName}
                  onChangeText={handleChange('displayName')}
                  onBlur={handleBlur('displayName')}
                  error={touched.displayName && !!errors.displayName}
                  style={styles.input}
                />
                {touched.displayName && errors.displayName ? (
                  <HelperText type="error" visible style={styles.helperText}>
                    {errors.displayName}
                  </HelperText>
                ) : (
                  <View style={styles.helperSpacer} />
                )}
                <Button
                  mode="contained"
                  onPress={() => handleSubmit()}
                  disabled={!isValid || !dirty || isUpdatingUsername}
                  loading={isUpdatingUsername}
                  style={[styles.button, styles.updateButton]}
                  labelStyle={styles.buttonLabel}
                >
                  Update Username
                </Button>
              </View>
            )}
          </Formik>
          <Button
            mode="outlined"
            onPress={changeEmail}
            disabled={isUpdatingEmail}
            loading={isUpdatingEmail}
            style={[styles.button, styles.emailButton]}
          >
            Change Email
          </Button>
          <Button
            mode="contained"
            onPress={logout}
            disabled={isLoggingOut}
            loading={isLoggingOut}
            style={[styles.button, styles.logoutButton]}
            labelStyle={styles.buttonLabel}
          >
            Logout
          </Button>
        </Surface>
      </ScrollView>
      {showLoadingOverlay && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator animating color="#4CAF50" size="large" />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollContainer: { paddingBottom: 40, paddingHorizontal: 20, paddingTop: 20 },
  header: { marginBottom: 20 },
  pageTitle: { fontWeight: '700' },
  pageSubtitle: { marginTop: 4, opacity: 0.65 },
  headerCard: { alignItems: 'center', borderRadius: 16, marginBottom: 20, padding: 24 },
  avatar: { backgroundColor: '#2563eb', marginBottom: 16 },
  avatarLabel: { fontWeight: 'bold' },
  userNameTitle: { fontSize: 22, fontWeight: 'bold' },
  userEmailSubtitle: { fontSize: 14, marginTop: 4 },
  formCard: { borderRadius: 16, marginBottom: 20, padding: 20 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 16 },
  input: { marginBottom: 4 },
  inputDisabled: { marginBottom: 16 },
  helperText: { marginBottom: 12 },
  helperSpacer: { height: 16 },
  button: { borderRadius: 8, marginBottom: 16, marginTop: 8, paddingVertical: 4 },
  updateButton: { backgroundColor: '#2563eb' },
  emailButton: { borderColor: '#2563eb' },
  logoutButton: { backgroundColor: '#dc2626', marginTop: 10 },
  buttonLabel: { fontSize: 15, fontWeight: 'bold' },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
    borderRadius: 16,
    justifyContent: 'center',
    zIndex: 10,
  },
});
