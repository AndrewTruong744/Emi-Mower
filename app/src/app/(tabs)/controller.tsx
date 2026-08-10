import { View } from 'react-native';
import Controls from '@/components/controller/Controls';
import { controllerStyles as styles } from '@/styles/controllerStyles';

export default function Controller() {
  return (
    <View style={styles.main}>
      <View style={styles.video}></View>
      <View style={styles.controller}>
        <Controls />
      </View>
    </View>
  );
}
