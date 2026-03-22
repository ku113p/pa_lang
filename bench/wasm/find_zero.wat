(module
  (memory (export "memory") 1)
  (func (export "find_zero") (param $ptr i32) (result i32)
    (local $mask i32)
    (local $zero v128)
    (block $found
      (loop $loop
        (local.set $mask
          (i8x16.bitmask
            (i8x16.eq (v128.load (local.get $ptr))
                      (local.get $zero))))
        (br_if $found (local.get $mask))
        (local.set $ptr (i32.add (local.get $ptr) (i32.const 16)))
        (br $loop)))
    (i32.add (local.get $ptr) (i32.ctz (local.get $mask)))))
