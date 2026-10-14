import gltest.direct.loader as direct_loader

_orig_patch = direct_loader._patch_run_nondet_for_direct_mode


def _custom_patch_run_nondet_for_direct_mode():
    _orig_patch()
    targets = []
    try:
        import genlayer.gl.vm as gl_vm1
        targets.append(gl_vm1)
    except (ImportError, AttributeError):
        pass
    try:
        import genlayer.vm as gl_vm2
        targets.append(gl_vm2)
    except (ImportError, AttributeError):
        pass
    for gl_vm in targets:
        if hasattr(gl_vm, "run_nondet"):
            gl_vm.run_nondet_unsafe = gl_vm.run_nondet


direct_loader._patch_run_nondet_for_direct_mode = _custom_patch_run_nondet_for_direct_mode
