import { ActivityIndicator, Modal, Portal, Text } from 'react-native-paper';
import { StyleSheet, View } from 'react-native';

export function CutoutUploadModal({ visible }: { visible: boolean }) {
  return (
    <Portal>
      <Modal visible={visible} dismissable={false} contentContainerStyle={styles.modal}>
        <View style={styles.content}>
          <ActivityIndicator size="large" />
          <Text variant="titleMedium" style={styles.text}>Uploading boundary cutout…</Text>
          <Text style={styles.detail}>The mower will receive it after the backend verifies the upload.</Text>
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  content: { alignItems: 'center', gap: 12 },
  detail: { color: '#D1D5DB', textAlign: 'center' },
  modal: { backgroundColor: '#1E1E1E', borderRadius: 16, margin: 24, padding: 20 },
  text: { color: '#FFFFFF', textAlign: 'center' },
});
