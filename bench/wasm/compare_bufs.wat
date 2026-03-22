(module
  (memory (export "memory") 1)
  (func (export "compare_bufs") (param $p1 i32) (param $p2 i32) (param $blocks i32) (result i32)
    (local $mask i32)
    (block $not_equal
      (block $done
        (loop $loop
          (br_if $done (i32.eqz (local.get $blocks)))
          (local.set $mask
            (i8x16.bitmask
              (i8x16.eq (v128.load (local.get $p1))
                        (v128.load (local.get $p2)))))
          (br_if $not_equal
            (i32.ne (local.get $mask) (i32.const 65535)))
          (local.set $p1 (i32.add (local.get $p1) (i32.const 16)))
          (local.set $p2 (i32.add (local.get $p2) (i32.const 16)))
          (local.set $blocks (i32.sub (local.get $blocks) (i32.const 1)))
          (br $loop)))
      (return (i32.const 0)))
    (i32.const 1)))
