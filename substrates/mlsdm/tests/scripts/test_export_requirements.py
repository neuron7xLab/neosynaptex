from scripts.ci import export_requirements


def _section_dependencies(lines, header, stop_prefixes):
    start_index = lines.index(header) + 1
    deps = []
    for line in lines[start_index:]:
        if any(line.startswith(prefix) for prefix in stop_prefixes):
            break
        if not line or line.startswith("#"):
            continue
        deps.append(line)
    return deps


def test_header_lists_all_optional_groups():
    pyproject = export_requirements.load_pyproject(export_requirements.PYPROJECT_PATH)
    deps = export_requirements.parse_pyproject_deps(pyproject)
    content = export_requirements.generate_requirements(deps)

    optional_groups = sorted(deps["optional"].keys())
    group_list = ", ".join(optional_groups)

    assert (
        f"# Optional dependency groups discovered in pyproject.toml: {group_list}" in content
    )
    assert (
        f"# Optional dependency groups included in this file: all ({group_list})" in content
    )
    assert "# Optional dependency groups excluded: none" in content
    assert "# Optional dependency packages excluded:" in content
    assert (
        "# - jupyter: excluded from requirements.txt to avoid pip-audit failures via nbconvert"
        " (CVE-2025-53000; remove once nbconvert>=7.16.0)"
        in content
    )
    assert (
        "# - jupyter-core: excluded from requirements.txt to avoid pip-audit failures via nbconvert"
        " (CVE-2025-53000; remove once nbconvert>=7.16.0)"
        in content
    )


def test_docs_and_neurolang_dependencies_present():
    pyproject = export_requirements.load_pyproject(export_requirements.PYPROJECT_PATH)
    deps = export_requirements.parse_pyproject_deps(pyproject)
    content = export_requirements.generate_requirements(deps)

    assert "sphinx>=7.0.0" in content
    assert "sphinx-rtd-theme>=2.0.0" in content
    assert "torch>=2.0.0" in content
    assert "jupyter>=1.0.0" not in content


def test_sections_are_sorted_and_deterministic():
    pyproject = export_requirements.load_pyproject(export_requirements.PYPROJECT_PATH)
    deps = export_requirements.parse_pyproject_deps(pyproject)
    content = export_requirements.generate_requirements(deps)
    lines = content.splitlines()

    optional_groups = sorted(deps["optional"].keys())
    optional_headers = [
        (
            group,
            (
                f"# Optional {export_requirements._title_case_group(group)} "
                f"(from pyproject.toml [project.optional-dependencies].{group})"
            ),
        )
        for group in optional_groups
    ]
    indices = [lines.index(header) for _, header in optional_headers]
    assert indices == sorted(indices)

    core_header = "# Core Dependencies (from pyproject.toml [project.dependencies])"
    stop_prefixes = ["# Optional ", "# Security:"]
    core_deps = _section_dependencies(lines, core_header, stop_prefixes)
    assert core_deps == sorted(core_deps, key=str.lower)
    assert core_deps == sorted(deps["core"], key=str.lower)

    optional_stop_prefixes = ["# Optional ", "# Security:"]
    for group, header in optional_headers:
        section_deps = _section_dependencies(lines, header, optional_stop_prefixes)
        assert section_deps == sorted(section_deps, key=str.lower)
        expected = export_requirements.filter_excluded_dependencies(deps["optional"][group])
        assert section_deps == sorted(expected, key=str.lower)


def test_excluded_dependency_name_variants_are_normalized():
    deps = [
        "Jupyter>=1.0.0",
        "jupyter_core>=5.0.0",
        "jupyter.core>=5.0.0",
        "numpy>=1.26.0",
    ]

    assert export_requirements.filter_excluded_dependencies(deps) == ["numpy>=1.26.0"]
