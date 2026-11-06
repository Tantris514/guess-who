UserEngine.ini (dev only): enables Python remote execution on loopback (multicast TTL 0) for the build scripts in Tools\, and limits shader-compile threads.
It is kept out of GuessWho\Config so it never ships in a package. To use the build scripts again, copy it back to GuessWho\Config\ and restart the editor; remove it again before packaging.
