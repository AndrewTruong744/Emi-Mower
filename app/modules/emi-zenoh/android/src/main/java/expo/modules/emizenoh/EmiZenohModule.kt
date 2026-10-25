package expo.modules.emizenoh

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import org.json.JSONObject

object RustBridge {
  init { System.loadLibrary("emi_zenoh_native") }
  @Volatile var listener: ((Map<String, Any>) -> Unit)? = null
  @JvmStatic external fun initialize()
  @JvmStatic external fun shutdown()
  @JvmStatic external fun call(request: ByteArray): ByteArray
  @JvmStatic fun onNativeEvent(bytes: ByteArray) {
    val data = JSONObject(bytes.toString(Charsets.UTF_8))
    listener?.invoke(mapOf("subscriptionId" to data.getString("subscriptionId"), "key" to data.getString("key"), "payload" to data.getString("payload"), "put" to data.getBoolean("put")))
  }
}
class EmiZenohModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("EmiZenoh")
    Events("sample")
    OnCreate {
      RustBridge.initialize()
      RustBridge.listener = { sample -> sendEvent("sample", sample) }
    }
    // JNI waits for a reply. Use Expo's shared I/O pool so one pending request
    // does not block the serial module queue or another request's promise.
    AsyncFunction("call") { request: String ->
      RustBridge.call(request.toByteArray(Charsets.UTF_8)).toString(Charsets.UTF_8)
    }.runOnQueue(appContext.backgroundCoroutineScope)
    OnDestroy {
      RustBridge.listener = null
      RustBridge.shutdown()
    }
  }
}
