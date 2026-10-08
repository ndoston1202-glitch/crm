plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "uz.crm.recorder"
    compileSdk = 34

    defaultConfig {
        applicationId = "uz.crm.recorder"
        minSdk = 26
        targetSdk = 34
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "1.0." + (System.getenv("GITHUB_RUN_NUMBER") ?: "0")
    }

    // Har safar bir xil kalit bilan imzolanadi — yangi versiya eskisining ustiga o'rnatiladi
    signingConfigs {
        create("crm") {
            storeFile = file("crm-release.keystore")
            storePassword = "crmrecorder"
            keyAlias = "crm"
            keyPassword = "crmrecorder"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("crm")
        }
        debug {
            signingConfig = signingConfigs.getByName("crm")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
