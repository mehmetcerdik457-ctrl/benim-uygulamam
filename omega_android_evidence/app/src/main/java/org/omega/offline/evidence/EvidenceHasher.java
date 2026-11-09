package org.omega.offline.evidence;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

/**
 * Stateless stream hasher. No file paths, device identifiers or file content are retained.
 * Must not be mistaken for source provenance, malware detection or signature validation.
 */
public final class EvidenceHasher {
    public static final long MAX_BYTES = 64L * 1024L * 1024L;
    private static final char[] HEX = "0123456789abcdef".toCharArray();

    private EvidenceHasher() {}

    public static final class Result {
        public final long bytes;
        public final String sha256;
        private Result(long bytes, String sha256) {
            this.bytes = bytes;
            this.sha256 = sha256;
        }
    }

    public static Result calculate(InputStream source) throws IOException {
        return calculate(source, MAX_BYTES);
    }

    // Package-private limit used for exact-boundary unit tests.
    static Result calculate(InputStream source, long limit) throws IOException {
        if (source == null || limit < 0 || limit > MAX_BYTES) {
            throw new IllegalArgumentException("Invalid input or limit");
        }
        final MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exc) {
            throw new IllegalStateException("SHA-256 is unavailable");
        }
        byte[] buffer = new byte[32 * 1024];
        long count = 0;
        while (true) {
            if (Thread.currentThread().isInterrupted()) {
                throw new IOException("Cancelled");
            }
            int length = source.read(buffer);
            if (length == -1) break;
            if (length == 0) {
                // Providers may return zero even with a nonempty buffer.
                int next = source.read();
                if (next == -1) break;
                if (count >= limit) throw new IOException("File too large");
                digest.update((byte) next);
                count++;
                continue;
            }
            if (length > limit - count) throw new IOException("File too large");
            digest.update(buffer, 0, length);
            count += length;
        }
        return new Result(count, toHex(digest.digest()));
    }

    public static boolean isValidExpectedHash(String text) {
        return text != null && text.matches("[a-fA-F0-9]{64}");
    }

    public static boolean matches(String expected, String actual) {
        if (!isValidExpectedHash(expected) || !isValidExpectedHash(actual)) return false;
        return MessageDigest.isEqual(fromHex(expected), fromHex(actual));
    }

    private static byte[] fromHex(String text) {
        byte[] out = new byte[32];
        for (int i = 0; i < out.length; i++) {
            int high = Character.digit(text.charAt(i * 2), 16);
            int low = Character.digit(text.charAt(i * 2 + 1), 16);
            out[i] = (byte) ((high << 4) | low);
        }
        return out;
    }

    private static String toHex(byte[] bytes) {
        char[] chars = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            chars[2 * i] = HEX[(bytes[i] & 0xff) >>> 4];
            chars[2 * i + 1] = HEX[bytes[i] & 0x0f];
        }
        return new String(chars).toLowerCase(Locale.ROOT);
    }
}
