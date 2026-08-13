import { StyleSheet, View } from 'react-native';
import Controls from '@/components/controller/Controls';

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

const styles = StyleSheet.create({
  main: {
    display: 'flex',
    flex: 1,
  },
  video: {
    backgroundColor: 'red',
    flex: 1,
  },
  controller: {
    alignItems: 'center',
    backgroundColor: 'rgb(100,100,100)',
    display: 'flex',
    flex: 1,
    justifyContent: 'center',
  },
});
