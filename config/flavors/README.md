## Naming flavor files

The default file name should be on the form:

```
<class-name>.yaml
<class-name>-<region>.yaml
```

Where `<class-name>` could be a short name like `m1` or long like `hpc.m1a`

If we use region in the file the flavor will always ONLY be in that region.
Otherwise the flavor will be in all regions.

NB! To avoid error messages you should always create both files when using
region, but only have the flavor types in the region specific one.
