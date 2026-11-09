package org.omega.offline.evidence;

import org.junit.Test;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import static org.junit.Assert.*;

public final class EvidenceHasherTest {
    private static final String ABC =
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

    @Test public void knownSha256MatchesExactBytes() throws Exception {
        EvidenceHasher.Result result=EvidenceHasher.calculate(
            new ByteArrayInputStream("abc".getBytes(StandardCharsets.US_ASCII)));
        assertEquals(3L,result.bytes);
        assertEquals(ABC,result.sha256);
        assertTrue(EvidenceHasher.matches(ABC,result.sha256));
        assertTrue(EvidenceHasher.matches(ABC.toUpperCase(),result.sha256));
        assertFalse(EvidenceHasher.matches("0".repeat(64),result.sha256));
    }
    @Test public void emptySourceHashIsKnownAndZeroBytes() throws Exception {
        EvidenceHasher.Result result=EvidenceHasher.calculate(new ByteArrayInputStream(new byte[0]));
        assertEquals(0L,result.bytes);
        assertEquals("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                result.sha256);
    }
    @Test public void malformedHashesNeverMatch() {
        assertFalse(EvidenceHasher.isValidExpectedHash(""));
        assertFalse(EvidenceHasher.isValidExpectedHash(" "+ABC));
        assertFalse(EvidenceHasher.isValidExpectedHash("g".repeat(64)));
        assertFalse(EvidenceHasher.matches(ABC.substring(1),ABC));
        assertFalse(EvidenceHasher.matches(null,ABC));
    }
    @Test public void strictSizeLimitAllowsExactLimit() throws Exception {
        EvidenceHasher.Result result=EvidenceHasher.calculate(
            new ByteArrayInputStream(new byte[8]),8);
        assertEquals(8L,result.bytes);
    }
    @Test public void sizeOverrunDeniesInsteadOfTruncating() throws Exception {
        try {
            EvidenceHasher.calculate(new ByteArrayInputStream(new byte[9]),8);
            fail("Over-limit stream must be rejected");
        } catch(IOException expected) {
            assertEquals("File too large",expected.getMessage());
        }
    }
    @Test public void nullStreamCannotBeHashed() {
        try {
            EvidenceHasher.calculate(null);
            fail("Null stream must be rejected");
        } catch(IllegalArgumentException expected) {
            assertNotNull(expected);
        } catch(IOException unexpected) {
            fail("Unexpected I/O error");
        }
    }
    @Test public void inaccessibleLimitsAreRejected() throws Exception {
        for(long limit:new long[]{-1L,EvidenceHasher.MAX_BYTES+1L}) {
            try {
                EvidenceHasher.calculate(new ByteArrayInputStream(new byte[0]),limit);
                fail("Invalid limit must fail");
            } catch(IllegalArgumentException expected) {
                assertNotNull(expected);
            }
        }
    }
}
