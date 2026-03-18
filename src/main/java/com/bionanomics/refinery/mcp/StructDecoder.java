package com.bionanomics.refinery.mcp;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Decodes well-known WPILib struct-encoded raw bytes from NetworkTables
 * into human-readable JSON objects. Supports both single structs and arrays.
 *
 * <p>WPILib struct encoding uses little-endian IEEE 754 doubles packed contiguously.
 * Array types are N copies of the struct packed back-to-back.
 *
 * <p>Supported types: Pose2d, Pose3d, Translation2d, Translation3d, Rotation2d,
 * Rotation3d, Quaternion, ChassisSpeeds, SwerveModuleState, SwerveModulePosition,
 * Twist2d, Transform2d.
 */
final class StructDecoder {
    private StructDecoder() {}

    /**
     * Attempt to decode a raw NT value given its type string.
     *
     * @param typeString the NT type string, e.g. "struct:Pose2d" or "struct:SwerveModuleState[]"
     * @param raw the raw bytes
     * @return a JsonMap, JsonList, or null if the type is not recognized
     */
    static Object decode(String typeString, byte[] raw) {
        if (typeString == null || raw == null || raw.length == 0) return null;
        if (!typeString.startsWith("struct:")) return null;

        String structPart = typeString.substring("struct:".length());
        boolean isArray = structPart.endsWith("[]");
        String typeName = isArray ? structPart.substring(0, structPart.length() - 2) : structPart;

        ByteBuffer buf = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);

        if (isArray) {
            return decodeArray(typeName, buf);
        } else {
            return decodeSingle(typeName, buf);
        }
    }

    private static JsonMap decodeSingle(String typeName, ByteBuffer buf) {
        int size = structSize(typeName);
        if (size <= 0 || buf.remaining() < size) return null;
        return decodeOne(typeName, buf);
    }

    private static JsonList decodeArray(String typeName, ByteBuffer buf) {
        int size = structSize(typeName);
        if (size <= 0 || buf.remaining() < size) return null;

        int count = buf.remaining() / size;
        JsonList list = new JsonList();
        for (int i = 0; i < count; i++) {
            JsonMap item = decodeOne(typeName, buf);
            if (item == null) break;
            list.add(item);
        }
        return list;
    }

    /** Returns the byte size of one instance of the named struct, or -1 if unknown. */
    private static int structSize(String typeName) {
        switch (typeName) {
            case "Rotation2d":          return 8;       // 1 double
            case "Translation2d":       return 16;      // 2 doubles
            case "Pose2d":              return 24;      // Translation2d + Rotation2d
            case "Transform2d":         return 24;      // Translation2d + Rotation2d
            case "Twist2d":             return 24;      // dx, dy, dtheta
            case "ChassisSpeeds":       return 24;      // vx, vy, omega
            case "SwerveModuleState":   return 16;      // speed + Rotation2d
            case "SwerveModulePosition":return 16;      // distance + Rotation2d
            case "Quaternion":          return 32;      // w, x, y, z
            case "Rotation3d":          return 32;      // Quaternion
            case "Translation3d":       return 24;      // x, y, z
            case "Pose3d":              return 56;      // Translation3d(24) + Rotation3d(32)
            default:                    return -1;
        }
    }

    /** Decode one struct instance from the buffer. Advances the buffer position. */
    private static JsonMap decodeOne(String typeName, ByteBuffer buf) {
        switch (typeName) {
            case "Rotation2d":          return decodeRotation2d(buf);
            case "Translation2d":       return decodeTranslation2d(buf);
            case "Pose2d":              return decodePose2d(buf);
            case "Transform2d":         return decodeTransform2d(buf);
            case "Twist2d":             return decodeTwist2d(buf);
            case "ChassisSpeeds":       return decodeChassisSpeeds(buf);
            case "SwerveModuleState":   return decodeSwerveModuleState(buf);
            case "SwerveModulePosition":return decodeSwerveModulePosition(buf);
            case "Quaternion":          return decodeQuaternion(buf);
            case "Rotation3d":          return decodeRotation3d(buf);
            case "Translation3d":       return decodeTranslation3d(buf);
            case "Pose3d":              return decodePose3d(buf);
            default:                    return null;
        }
    }

    // ---- Individual struct decoders ----

    private static JsonMap decodeRotation2d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("radians", buf.getDouble());
        return m;
    }

    private static JsonMap decodeTranslation2d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("x", buf.getDouble());
        m.put("y", buf.getDouble());
        return m;
    }

    private static JsonMap decodePose2d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("translation", decodeTranslation2d(buf));
        m.put("rotation", decodeRotation2d(buf));
        return m;
    }

    private static JsonMap decodeTransform2d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("translation", decodeTranslation2d(buf));
        m.put("rotation", decodeRotation2d(buf));
        return m;
    }

    private static JsonMap decodeTwist2d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("dx", buf.getDouble());
        m.put("dy", buf.getDouble());
        m.put("dtheta", buf.getDouble());
        return m;
    }

    private static JsonMap decodeChassisSpeeds(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("vx", buf.getDouble());
        m.put("vy", buf.getDouble());
        m.put("omega", buf.getDouble());
        return m;
    }

    private static JsonMap decodeSwerveModuleState(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("speed", buf.getDouble());
        m.put("angle", decodeRotation2d(buf));
        return m;
    }

    private static JsonMap decodeSwerveModulePosition(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("distance", buf.getDouble());
        m.put("angle", decodeRotation2d(buf));
        return m;
    }

    private static JsonMap decodeQuaternion(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("w", buf.getDouble());
        m.put("x", buf.getDouble());
        m.put("y", buf.getDouble());
        m.put("z", buf.getDouble());
        return m;
    }

    private static JsonMap decodeRotation3d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("quaternion", decodeQuaternion(buf));
        return m;
    }

    private static JsonMap decodeTranslation3d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("x", buf.getDouble());
        m.put("y", buf.getDouble());
        m.put("z", buf.getDouble());
        return m;
    }

    private static JsonMap decodePose3d(ByteBuffer buf) {
        JsonMap m = new JsonMap();
        m.put("translation", decodeTranslation3d(buf));
        m.put("rotation", decodeRotation3d(buf));
        return m;
    }
}
