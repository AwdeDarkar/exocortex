A manager holds some useful form of global context or state. These should have a very light touch to
avoid repeating redux hell or holding unnecessary data in cookies or local storage. In an ideal
world perhaps everything would be 'truely stateless' but in rich, reactive, modern-feeling UIs
that's frankly impossible.
