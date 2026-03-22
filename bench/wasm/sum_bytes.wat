(module
  (memory (export "memory") 1)
  (func (export "sum_bytes") (param $ptr i32) (param $len i32) (result i32)
    (local $acc i32)
    (block $break
      (loop $loop
        (br_if $break (i32.eqz (local.get $len)))
        (local.set $acc
          (i32.add (local.get $acc)
                   (i32.load8_u (local.get $ptr))))
        (local.set $ptr (i32.add (local.get $ptr) (i32.const 1)))
        (local.set $len (i32.sub (local.get $len) (i32.const 1)))
        (br $loop)))
    (local.get $acc)))
