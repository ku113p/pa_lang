(module
  (func (export "fibonacci") (param $n i32) (result i32)
    (local $a i32)
    (local $b i32)
    (local $tmp i32)
    (local.set $b (i32.const 1))
    (block $break
      (loop $loop
        (br_if $break (i32.eqz (local.get $n)))
        (local.set $tmp (i32.add (local.get $a) (local.get $b)))
        (local.set $a (local.get $b))
        (local.set $b (local.get $tmp))
        (local.set $n (i32.sub (local.get $n) (i32.const 1)))
        (br $loop)))
    (local.get $a)))
