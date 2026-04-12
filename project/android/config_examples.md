<!-- 1. AndroidManifest.xml Entry -->
<!-- Add this to your project's AndroidManifest.xml -->

<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    
    <!-- Health Connect Permissions -->
    <uses-permission android:name="android.permission.health.READ_STEPS"/>
    <uses-permission android:name="android.permission.health.READ_HEART_RATE"/>
    <uses-permission android:name="android.permission.health.READ_SLEEP"/>

    <queries>
        <package android:name="com.google.android.apps.healthdata" />
    </queries>

    <application>
        <!-- Health Connect Activity for permission management -->
        <activity
            android:name=".HealthConnectActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>
        </activity>
    </application>
</manifest>

<!-- 2. build.gradle (Module level) dependencies -->
dependencies {
    implementation "androidx.health.connect:connect-client:1.1.0-alpha11"
    implementation "androidx.work:work-runtime-kotlin:2.8.1"
    implementation "com.google.guava:guava:31.1-android"
}
