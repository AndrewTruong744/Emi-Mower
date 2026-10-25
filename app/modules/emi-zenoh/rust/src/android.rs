//! Android's JNI boundary. Zenoh operations stay in Rust; no C++ shim is needed.
use jni::{
    errors::Result as JniResult,
    objects::{GlobalRef, JByteArray, JClass, JValue},
    sys::jbyteArray,
    JNIEnv, JavaVM,
};
use std::{
    panic::{catch_unwind, AssertUnwindSafe},
    ptr,
    sync::{Mutex, OnceLock},
};

static JVM: OnceLock<JavaVM> = OnceLock::new();
static BRIDGE: Mutex<Option<GlobalRef>> = Mutex::new(None);

// Never unwind into Android. Preserve existing Java exceptions (for example OOM)
// and translate other boundary failures into exceptions rejected by Expo.
fn boundary<T>(
    env: &mut JNIEnv,
    fallback: T,
    operation: impl FnOnce(&mut JNIEnv) -> Result<T, String>,
) -> T {
    let result = catch_unwind(AssertUnwindSafe(|| operation(env)))
        .unwrap_or_else(|_| Err("Native Zenoh JNI operation panicked".into()));
    match result {
        Ok(value) => value,
        Err(error) => {
            if !env.exception_check().unwrap_or(true) {
                let _ = env.throw_new("java/lang/IllegalStateException", error);
            }
            fallback
        }
    }
}

#[no_mangle]
pub extern "system" fn Java_expo_modules_emizenoh_RustBridge_initialize(
    mut env: JNIEnv,
    class: JClass,
) {
    boundary(&mut env, (), |env| {
        env.get_static_method_id(&class, "onNativeEvent", "([B)V")
            .map_err(|e| e.to_string())?;
        let vm = env.get_java_vm().map_err(|e| e.to_string())?;
        let bridge = env.new_global_ref(class).map_err(|e| e.to_string())?;
        let _ = JVM.set(vm);
        *BRIDGE.lock().map_err(|e| e.to_string())? = Some(bridge);
        Ok(())
    });
}

#[no_mangle]
pub extern "system" fn Java_expo_modules_emizenoh_RustBridge_call(
    mut env: JNIEnv,
    _class: JClass,
    request: JByteArray,
) -> jbyteArray {
    boundary(&mut env, ptr::null_mut(), |env| {
        let request = env.convert_byte_array(request).map_err(|e| e.to_string())?;
        let response = super::call_json(&request);
        env.byte_array_from_slice(response.as_bytes())
            .map(JByteArray::into_raw)
            .map_err(|e| e.to_string())
    })
}

#[no_mangle]
pub extern "system" fn Java_expo_modules_emizenoh_RustBridge_shutdown(
    mut env: JNIEnv,
    _class: JClass,
) {
    boundary(&mut env, (), |_| {
        *BRIDGE.lock().map_err(|e| e.to_string())? = None;
        super::shutdown();
        Ok(())
    });
}

pub(super) fn emit(bytes: &[u8]) {
    let Some(vm) = JVM.get() else { return };
    // Clone the global reference before releasing the lock so shutdown cannot
    // invalidate a class while a worker is delivering an event.
    let bridge = BRIDGE.lock().unwrap().clone();
    let Some(bridge) = bridge else { return };
    let Ok(mut env) = vm.attach_current_thread() else {
        return;
    };
    let _ = env.with_local_frame(4, |env| -> JniResult<()> {
        let array = env.byte_array_from_slice(bytes)?;
        let class: &JClass = bridge.as_obj().into();
        env.call_static_method(class, "onNativeEvent", "([B)V", &[JValue::Object(&array)])?;
        Ok(())
    });
    // A listener failure must not leave a pending exception on a Rust worker.
    if env.exception_check().unwrap_or(false) {
        let _ = env.exception_clear();
    }
}

#[cfg(all(test, feature = "jni-tests", not(target_os = "android")))]
mod tests;
