(module
  (memory (export "memory") 1)
  (func (export "xor_buffer") (param $ptr i32) (param $key i32) (param $len i32)
    (block $break
      (loop $loop
        (br_if $break (i32.eqz (local.get $len)))
        (i32.store8 (local.get $ptr)
          (i32.xor (i32.load8_u (local.get $ptr))
                   (local.get $key)))
        (local.set $ptr (i32.add (local.get $ptr) (i32.const 1)))
        (local.set $len (i32.sub (local.get $len) (i32.const 1)))
        (br $loop)))))
