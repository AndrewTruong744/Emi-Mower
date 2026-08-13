import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text, TextInput, Button, Avatar, HelperText, ActivityIndicator } from 'react-native-paper';
import { Formik } from 'formik';
import { useSettings } from '@/hooks/useSettings';

interface FormValues {
  displayName: string;
}

const validate = (values: FormValues) => {
  const errors: { displayName?: string } = {};
  if (!values.displayName) {
    errors.displayName = 'Name is required';
  } else if (!/^[a-zA-Z0-9_]+$/.test(values.displayName)) {
    // Standard alphanumeric allowing underscores for versatility
    errors.displayName = 'Name must be alphanumeric';
  } else if (values.displayName.length > 32) {
    errors.displayName = 'Name must be at most 32 characters';
  }
  return errors;
};

export default function SettingsScreen() {
  const {
    user,
    updateUsername,
    changeEmail,
    logout,
    isUpdatingUsername,
    isUpdatingEmail,
    isLoggingOut,
  } = useSettings();

  const getInitials = (name: string | null) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  };

  const showLoadingOverlay = isUpdatingUsername || isUpdatingEmail || isLoggingOut;

  return (
    <View style={settingsStyles.container}>
      <ScrollView contentContainerStyle={settingsStyles.scrollContainer}>
        {/* Header Profile Section */}
        <View style={settingsStyles.headerCard}>
          <Avatar.Text
            size={80}
            label={getInitials(user.displayName)}
            style={settingsStyles.avatar}
            labelStyle={{ fontWeight: 'bold' }}
          />
          <Text style={settingsStyles.userNameTitle}>{user.displayName || 'No Name Set'}</Text>
          <Text style={settingsStyles.userEmailSubtitle}>{user.email || 'No Email Set'}</Text>
        </View>

        {/* Profile Details & Form Card */}
        <View style={settingsStyles.formCard}>
          <Text style={settingsStyles.cardTitle}>Account Settings</Text>

          {/* User ID Field (Uneditable) */}
          <TextInput
            mode="outlined"
            label="User ID (UID)"
            value={user.user_id || ''}
            editable={false}
            disabled
            style={settingsStyles.inputDisabled}
            outlineColor="#333"
            activeOutlineColor="#333"
            textColor="#888"
          />

          {/* Email Address Field (Uneditable) */}
          <TextInput
            mode="outlined"
            label="Email Address"
            value={user.email || ''}
            editable={false}
            disabled
            style={settingsStyles.inputDisabled}
            outlineColor="#333"
            activeOutlineColor="#333"
            textColor="#888"
          />

          {/* Editable Display Name Form */}
          <Formik
            initialValues={{ displayName: user.displayName || '' }}
            enableReinitialize
            validate={validate}
            onSubmit={async (values) => {
              await updateUsername(values.displayName);
            }}
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
                  style={settingsStyles.input}
                  outlineColor="#444"
                  activeOutlineColor="#4CAF50"
                  textColor="#FFFFFF"
                />
                {touched.displayName && errors.displayName ? (
                  <HelperText type="error" visible={true} style={settingsStyles.helperText}>
                    {errors.displayName}
                  </HelperText>
                ) : (
                  <View style={{ height: 16 }} />
                )}

                <Button
                  mode="contained"
                  onPress={() => handleSubmit()}
                  disabled={!isValid || !dirty || isUpdatingUsername}
                  loading={isUpdatingUsername}
                  style={[settingsStyles.button, settingsStyles.updateButton]}
                  labelStyle={settingsStyles.buttonLabel}
                >
                  Update Username
                </Button>
              </View>
            )}
          </Formik>

          {/* Change Email Trigger */}
          <Button
            mode="outlined"
            onPress={changeEmail}
            disabled={isUpdatingEmail}
            loading={isUpdatingEmail}
            style={[settingsStyles.button, settingsStyles.emailButton]}
            labelStyle={[settingsStyles.buttonLabel, { color: '#4CAF50' }]}
            textColor="#4CAF50"
          >
            Change Email
          </Button>

          {/* Logout Action */}
          <Button
            mode="contained"
            onPress={logout}
            disabled={isLoggingOut}
            loading={isLoggingOut}
            style={[settingsStyles.button, settingsStyles.logoutButton]}
            labelStyle={settingsStyles.buttonLabel}
          >
            Logout
          </Button>
        </View>
      </ScrollView>

      {/* Global Activity Overlay */}
      {showLoadingOverlay && (
        <View style={settingsStyles.loadingOverlay}>
          <ActivityIndicator animating={true} color="#4CAF50" size="large" />
        </View>
      )}
    </View>
  );
}

const settingsStyles = StyleSheet.create({
  container: {
    backgroundColor: '#121212',
    flex: 1,
    padding: 20,
  },
  scrollContainer: {
    paddingBottom: 40,
  },
  headerCard: {
    alignItems: 'center',
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    elevation: 8,
    marginBottom: 20,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  avatar: {
    backgroundColor: '#4CAF50',
    marginBottom: 16,
  },
  userNameTitle: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: 'bold',
  },
  userEmailSubtitle: {
    color: '#B0B0B0',
    fontSize: 14,
    marginTop: 4,
  },
  formCard: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    elevation: 8,
    marginBottom: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  cardTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
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
    marginBottom: 16,
    marginTop: 8,
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
    fontSize: 15,
    fontWeight: 'bold',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    backgroundColor: 'rgba(18, 18, 18, 0.7)',
    borderRadius: 16,
    justifyContent: 'center',
    zIndex: 10,
  },
});
