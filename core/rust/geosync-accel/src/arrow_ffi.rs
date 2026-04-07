// GEOSYNC-ACCEL — Apache Arrow C-Data Interface FFI
//
// Implements zero-copy columnar data exchange via Arrow C-Data Interface.
// Enables seamless interop with Polars, DuckDB, GeoParquet readers, and
// any Arrow-compatible analytics engine without serialization overhead.
//
// The Arrow C-Data Interface defines two C structs: ArrowSchema and ArrowArray.
// We use the `arrow` crate's FFI module to produce/consume these structs,
// then wrap them in PyCapsules for Python-side exchange (PyArrow protocol).
//
// Reference: https://arrow.apache.org/docs/format/CDataInterface.html
// SPDX-License-Identifier: AGPL-3.0-or-later

use arrow::array::{Array, ArrayRef, Float64Array};
use arrow::datatypes::{DataType, Field, Schema};
use arrow::ffi::{FFI_ArrowArray, FFI_ArrowSchema};
use arrow::record_batch::RecordBatch;
use pyo3::ffi as pyffi;
use pyo3::prelude::*;
use std::ffi::CString;
use std::os::raw::c_void;
use std::sync::Arc;

/// Error types for Arrow FFI operations.
#[derive(Debug, thiserror::Error)]
pub enum ArrowFfiError {
    #[error("Arrow error: {0}")]
    Arrow(#[from] arrow::error::ArrowError),
    #[error("Python error: {0}")]
    Python(String),
    #[error("Schema mismatch: expected {expected}, got {actual}")]
    SchemaMismatch { expected: String, actual: String },
}

impl From<ArrowFfiError> for PyErr {
    fn from(err: ArrowFfiError) -> PyErr {
        pyo3::exceptions::PyValueError::new_err(err.to_string())
    }
}

/// Schema for gamma-scaling data: (topo: f64, cost: f64)
pub fn gamma_schema() -> Schema {
    Schema::new(vec![
        Field::new("topo", DataType::Float64, false),
        Field::new("cost", DataType::Float64, false),
    ])
}

/// Schema for Hilbert-indexed geo-coordinates: (x: f64, y: f64, hilbert_idx: u64)
pub fn hilbert_geo_schema() -> Schema {
    Schema::new(vec![
        Field::new("x", DataType::Float64, false),
        Field::new("y", DataType::Float64, false),
        Field::new("hilbert_idx", DataType::UInt64, false),
    ])
}

/// Create an Arrow RecordBatch from topo/cost vectors (zero-copy from Rust).
pub fn gamma_data_to_record_batch(topo: Vec<f64>, cost: Vec<f64>) -> Result<RecordBatch, ArrowFfiError> {
    let schema = Arc::new(gamma_schema());
    let topo_array: ArrayRef = Arc::new(Float64Array::from(topo));
    let cost_array: ArrayRef = Arc::new(Float64Array::from(cost));
    Ok(RecordBatch::try_new(schema, vec![topo_array, cost_array])?)
}

/// Export an Arrow Float64Array as a pair of PyCapsules (ArrowSchema + ArrowArray).
///
/// This follows the Arrow PyCapsule Interface (standardized in 2024+):
/// - Schema capsule name: "arrow_schema"
/// - Array capsule name: "arrow_array"
pub fn export_f64_array_to_capsules(
    py: Python<'_>,
    data: Vec<f64>,
) -> PyResult<(PyObject, PyObject)> {
    let array = Float64Array::from(data);
    let data = array.to_data();

    let ffi_array = FFI_ArrowArray::new(&data);
    let ffi_schema = FFI_ArrowSchema::try_from(data.data_type())
        .map_err(|e: arrow::error::ArrowError| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    // Box and export as PyCapsules
    let schema_ptr = Box::into_raw(Box::new(ffi_schema));
    let array_ptr = Box::into_raw(Box::new(ffi_array));

    let schema_name = CString::new("arrow_schema").unwrap();
    let array_name = CString::new("arrow_array").unwrap();

    let schema_capsule = unsafe {
        pyffi::PyCapsule_New(
            schema_ptr as *mut c_void,
            schema_name.as_ptr(),
            Some(drop_schema_capsule),
        )
    };

    let array_capsule = unsafe {
        pyffi::PyCapsule_New(
            array_ptr as *mut c_void,
            array_name.as_ptr(),
            Some(drop_array_capsule),
        )
    };

    if schema_capsule.is_null() || array_capsule.is_null() {
        return Err(pyo3::exceptions::PyMemoryError::new_err(
            "Failed to create Arrow PyCapsules",
        ));
    }

    // Intentionally leak CStrings — CPython holds the name pointers
    std::mem::forget(schema_name);
    std::mem::forget(array_name);

    Ok(unsafe {
        (
            PyObject::from_owned_ptr(py, schema_capsule),
            PyObject::from_owned_ptr(py, array_capsule),
        )
    })
}

/// Capsule destructor for ArrowSchema.
unsafe extern "C" fn drop_schema_capsule(capsule: *mut pyffi::PyObject) {
    let name = CString::new("arrow_schema").unwrap();
    let ptr = unsafe { pyffi::PyCapsule_GetPointer(capsule, name.as_ptr()) };
    if !ptr.is_null() {
        drop(unsafe { Box::from_raw(ptr as *mut FFI_ArrowSchema) });
    }
}

/// Capsule destructor for ArrowArray.
unsafe extern "C" fn drop_array_capsule(capsule: *mut pyffi::PyObject) {
    let name = CString::new("arrow_array").unwrap();
    let ptr = unsafe { pyffi::PyCapsule_GetPointer(capsule, name.as_ptr()) };
    if !ptr.is_null() {
        drop(unsafe { Box::from_raw(ptr as *mut FFI_ArrowArray) });
    }
}

/// Import an Arrow PyCapsule pair back into a Rust Float64Array.
///
/// This consumes the capsules — the Python side must not reuse them.
pub fn import_f64_array_from_capsules(
    _py: Python<'_>,
    schema_capsule: &Bound<'_, pyo3::types::PyAny>,
    array_capsule: &Bound<'_, pyo3::types::PyAny>,
) -> PyResult<Vec<f64>> {
    let schema_name = CString::new("arrow_schema").unwrap();
    let array_name = CString::new("arrow_array").unwrap();

    let schema_ptr = unsafe {
        pyffi::PyCapsule_GetPointer(schema_capsule.as_ptr(), schema_name.as_ptr())
    };
    let array_ptr = unsafe {
        pyffi::PyCapsule_GetPointer(array_capsule.as_ptr(), array_name.as_ptr())
    };

    if schema_ptr.is_null() || array_ptr.is_null() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Invalid Arrow capsules",
        ));
    }

    let ffi_schema = unsafe { std::ptr::read(schema_ptr as *const FFI_ArrowSchema) };
    let ffi_array = unsafe { std::ptr::read(array_ptr as *const FFI_ArrowArray) };

    let data = unsafe {
        arrow::ffi::from_ffi(ffi_array, &ffi_schema)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?
    };

    let array = Float64Array::from(data);
    Ok(array.values().to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gamma_schema_fields() {
        let schema = gamma_schema();
        assert_eq!(schema.fields().len(), 2);
        assert_eq!(schema.field(0).name(), "topo");
        assert_eq!(schema.field(1).name(), "cost");
    }

    #[test]
    fn test_record_batch_creation() {
        let topo = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let cost = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let batch = gamma_data_to_record_batch(topo, cost).unwrap();
        assert_eq!(batch.num_rows(), 5);
        assert_eq!(batch.num_columns(), 2);
    }
}
