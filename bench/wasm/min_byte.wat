(module
  (memory (export "memory") 1)
  (func (export "min_byte") (param $ptr i32) (param $len i32) (result i32)
    (local $min i32)
    (local $cur i32)
    (local.set $min (i32.load8_u (local.get $ptr)))
    (local.set $ptr (i32.add (local.get $ptr) (i32.const 1)))
    (local.set $len (i32.sub (local.get $len) (i32.const 1)))
    (block $break
      (loop $loop
        (br_if $break (i32.eqz (local.get $len)))
        (local.set $cur (i32.load8_u (local.get $ptr)))
        (if (i32.lt_u (local.get $cur) (local.get $min))
          (then (local.set $min (local.get $cur))))
        (local.set $ptr (i32.add (local.get $ptr) (i32.const 1)))
        (local.set $len (i32.sub (local.get $len) (i32.const 1)))
        (br $loop)))
    (local.get $min)))
