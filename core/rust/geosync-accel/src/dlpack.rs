// GEOSYNC-ACCEL — DLPack Zero-Copy Tensor Exchange
//
// Implements the DLPack v1.0 protocol for zero-copy tensor sharing between
// Rust, PyTorch, JAX, CuPy, and any DLPack-aware framework.
// Tensors are exchanged via PyCapsule containing a DLManagedTensor struct.
//
// Reference: https://dmlc.github.io/dlpack/latest/
// SPDX-License-Identifier: AGPL-3.0-or-later

use pyo3::ffi;
use pyo3::prelude::*;
use std::ffi::CString;
use std::os::raw::c_void;

/// DLPack device type codes.
#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DLDeviceType {
    Cpu = 1,
    Cuda = 2,
    CudaManaged = 13,
    Rocm = 10,
    Metal = 8,
    OneApi = 14,
}

/// DLPack data type codes.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DLDataTypeCode {
    Int = 0,
    UInt = 1,
    Float = 2,
    Bfloat = 4,
}

/// DLPack device descriptor.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct DLDevice {
    pub device_type: i32,
    pub device_id: i32,
}

/// DLPack data type descriptor.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct DLDataType {
    pub code: u8,
    pub bits: u8,
    pub lanes: u16,
}

/// DLPack tensor descriptor (v1.0).
#[repr(C)]
pub struct DLTensor {
    pub data: *mut c_void,
    pub device: DLDevice,
    pub ndim: i32,
    pub dtype: DLDataType,
    pub shape: *mut i64,
    pub strides: *mut i64,
    pub byte_offset: u64,
}

/// DLPack managed tensor with destructor for safe deallocation.
#[repr(C)]
pub struct DLManagedTensor {
    pub dl_tensor: DLTensor,
    pub manager_ctx: *mut c_void,
    pub deleter: Option<unsafe extern "C" fn(*mut DLManagedTensor)>,
}

/// Owned buffer that backs a DLPack capsule exported from Rust.
struct OwnedDLPackBuffer {
    data: Vec<f64>,
    shape: Vec<i64>,
    strides: Vec<i64>,
    managed: *mut DLManagedTensor,
}

/// Safety: The buffer is Send because it owns all its data exclusively.
unsafe impl Send for OwnedDLPackBuffer {}

/// Destructor called when the PyCapsule is garbage-collected on the Python side.
unsafe extern "C" fn dlpack_deleter(tensor: *mut DLManagedTensor) {
    if tensor.is_null() {
        return;
    }
    // Reconstruct the Box to drop the owned buffer
    let ctx = unsafe { (*tensor).manager_ctx };
    if !ctx.is_null() {
        drop(unsafe { Box::from_raw(ctx as *mut OwnedDLPackBuffer) });
    }
    drop(unsafe { Box::from_raw(tensor) });
}

/// PyCapsule destructor trampoline (called by CPython).
unsafe extern "C" fn capsule_destructor(capsule: *mut ffi::PyObject) {
    let name = CString::new("dltensor").unwrap();
    let ptr = unsafe { ffi::PyCapsule_GetPointer(capsule, name.as_ptr()) };
    if !ptr.is_null() {
        let managed = ptr as *mut DLManagedTensor;
        if let Some(deleter) = unsafe { (*managed).deleter } {
            unsafe { deleter(managed) };
        }
    }
}

/// Export a Rust `Vec<f64>` as a DLPack PyCapsule (zero-copy to consumer).
///
/// The returned PyCapsule follows the `__dlpack__` protocol:
/// - capsule name: "dltensor"
/// - consumer calls PyCapsule_GetPointer, takes ownership, renames to "used_dltensor"
pub fn vec_to_dlpack_capsule(py: Python<'_>, data: Vec<f64>) -> PyResult<PyObject> {
    let n = data.len();
    let mut shape = vec![n as i64];
    let mut strides = vec![1i64];

    let dl_tensor = DLTensor {
        data: data.as_ptr() as *mut c_void,
        device: DLDevice {
            device_type: DLDeviceType::Cpu as i32,
            device_id: 0,
        },
        ndim: 1,
        dtype: DLDataType {
            code: DLDataTypeCode::Float as u8,
            bits: 64,
            lanes: 1,
        },
        shape: shape.as_mut_ptr(),
        strides: strides.as_mut_ptr(),
        byte_offset: 0,
    };

    let managed = Box::into_raw(Box::new(DLManagedTensor {
        dl_tensor,
        manager_ctx: std::ptr::null_mut(),
        deleter: Some(dlpack_deleter),
    }));

    let owned = Box::new(OwnedDLPackBuffer {
        data,
        shape,
        strides,
        managed,
    });

    // Patch pointers to the owned heap allocations
    unsafe {
        (*managed).dl_tensor.data = owned.data.as_ptr() as *mut c_void;
        (*managed).dl_tensor.shape = owned.shape.as_ptr() as *mut i64;
        (*managed).dl_tensor.strides = owned.strides.as_ptr() as *mut i64;
        (*managed).manager_ctx = Box::into_raw(owned) as *mut c_void;
    }

    let name = CString::new("dltensor").map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("CString error: {e}"))
    })?;

    let capsule = unsafe {
        ffi::PyCapsule_New(
            managed as *mut c_void,
            name.as_ptr(),
            Some(capsule_destructor),
        )
    };

    if capsule.is_null() {
        return Err(pyo3::exceptions::PyMemoryError::new_err(
            "Failed to create DLPack PyCapsule",
        ));
    }

    Ok(unsafe { PyObject::from_owned_ptr(py, capsule) })
}

/// Import a DLPack PyCapsule from Python into a Rust slice view.
///
/// Safety: The consumer must ensure the capsule is a valid "dltensor" capsule.
/// After consumption, the capsule is renamed to "used_dltensor" per protocol.
pub fn dlpack_capsule_to_slice<'a>(
    _py: Python<'a>,
    capsule: &Bound<'a, pyo3::types::PyAny>,
) -> PyResult<&'a [f64]> {
    let capsule_ptr = capsule.as_ptr();

    let name = CString::new("dltensor").map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("CString error: {e}"))
    })?;

    let ptr = unsafe { ffi::PyCapsule_GetPointer(capsule_ptr, name.as_ptr()) };
    if ptr.is_null() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Invalid DLPack capsule: null pointer",
        ));
    }

    let managed = unsafe { &*(ptr as *const DLManagedTensor) };
    let tensor = &managed.dl_tensor;

    // Validate: must be CPU f64
    if tensor.device.device_type != DLDeviceType::Cpu as i32 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Only CPU tensors supported in this path",
        ));
    }
    if tensor.dtype.bits != 64 || tensor.dtype.code != DLDataTypeCode::Float as u8 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Expected float64 DLPack tensor",
        ));
    }

    let n = if tensor.ndim == 1 {
        (unsafe { *tensor.shape }) as usize
    } else {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Expected 1-D DLPack tensor",
        ));
    };

    let data_ptr = unsafe { (tensor.data as *const u8).add(tensor.byte_offset as usize) };
    let slice = unsafe { std::slice::from_raw_parts(data_ptr as *const f64, n) };

    // Rename to "used_dltensor" per DLPack protocol
    let used_name = CString::new("used_dltensor").unwrap();
    unsafe {
        ffi::PyCapsule_SetName(capsule_ptr, used_name.as_ptr());
    }
    // Leak the CString intentionally — CPython holds the pointer
    std::mem::forget(used_name);

    Ok(slice)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dlpack_struct_sizes() {
        // Verify C-compatible struct layout
        assert_eq!(std::mem::size_of::<DLDevice>(), 8);
        assert_eq!(std::mem::size_of::<DLDataType>(), 4);
    }

    #[test]
    fn test_device_type_codes() {
        assert_eq!(DLDeviceType::Cpu as i32, 1);
        assert_eq!(DLDeviceType::Cuda as i32, 2);
    }
}
