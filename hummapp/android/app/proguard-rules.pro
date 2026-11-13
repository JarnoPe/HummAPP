# Keep Retrofit & Gson models intact
-keepattributes Signature
-keepattributes *Annotation*
-keep class fi.hummapp.android.data.model.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
