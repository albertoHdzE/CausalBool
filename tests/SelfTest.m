Get["src/Packages/Integration/SelfTest.m"]
res = SelfTestRun[]
Export[FileNameJoin[{"results", "selftest", "Status.txt"}], {"OK", DateString[]}, "Text"]