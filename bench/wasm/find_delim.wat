(module
  (memory (export "memory") 1)
  (func (export "find_delim") (param $ptr i32) (param $delim i32) (param $blocks i32) (result i32)
    (local $mask i32)
    (local $splat v128)
    (local.set $splat (i8x16.splat (local.get $delim)))
    (block $found
      (block $not_found
        (loop $loop
          (br_if $not_found (i32.eqz (local.get $blocks)))
          (local.set $mask
            (i8x16.bitmask
              (i8x16.eq (v128.load (local.get $ptr))
                        (local.get $splat))))
          (br_if $found (local.get $mask))
          (local.set $ptr (i32.add (local.get $ptr) (i32.const 16)))
          (local.set $blocks (i32.sub (local.get $blocks) (i32.const 1)))
          (br $loop)))
      (return (i32.const 0)))
    (i32.add (local.get $ptr) (i32.ctz (local.get $mask)))))
