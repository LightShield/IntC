# Attribution — OGRE TransformSpace

- [OGRECave/ogre](https://github.com/OGRECave/ogre) `OgreMain/include/OgreNode.h`, tag **v14.2.5**, `0d90297a387f5eb0d6cfa9e5ab17879bb0123316`

**What we kept.** A 3-valued space tag on a command, used to pick a scale.

**What we changed.** C struct, `int space` (unscoped enums are 32-bit in C too), integer `x`. No scene graph, no float. The rewrite narrows `space` to `uint8_t`.
