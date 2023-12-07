#include <ctype.h>
#include <errno.h>
#include <libgen.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <stdbool.h>

#include <net/if.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/uio.h>

#include <linux/can.h>
#include <linux/can/raw.h>
#include <linux/net_tstamp.h>

enum ChainCountUnit {
    METER=0x1,
    FEET=0x2,
};
    
struct CH1203FrameChainCount {
    uint32_t unitcount;
    uint16_t unit;
};

struct CH1203Frame {
    int8_t isInvalid;
    struct CH1203FrameChainCount chainCount;
};

enum CH1203FrameType {
    MISC_FLAG_TYPE=0x6C0,
    CHAIN_COUNT_TYPE=0x6C1,
};

void parseCH1203Frame(uint16_t arbitrationId, uint8_t payloadLen, uint8_t* canPayload, struct CH1203Frame* parseOutput){
    parseOutput->isInvalid=true;
    
    if(8!=payloadLen){
        return;
    }
    
    if(0xC1 != canPayload[0] || 0x18 != canPayload[1]){
        return;
    }
    
    if(0x6C1==arbitrationId){
        parseOutput->chainCount.unitcount=*((uint32_t*) (canPayload+2));
        parseOutput->chainCount.unit=*((uint16_t*) (canPayload+6));
        parseOutput->isInvalid=false;
    }
}

#define assertEquals(expected, actual) \
{\
    if(expected!=actual){ \
        printf("Assertion failed at %s:%d expected %d but was %d\n", __FILE__, __LINE__, expected, actual); \
    } \
}

int main(){
    struct CH1203Frame parseOutput;
    memset(&parseOutput, 0, sizeof(parseOutput));
    parseCH1203Frame(MISC_FLAG_TYPE, 8, "\xC1\x18\x78\x00\x01\x00\x01\x00", &parseOutput);
    assertEquals(true, parseOutput.isInvalid);

    parseCH1203Frame(CHAIN_COUNT_TYPE, 8, "\xC1\x18\x6B\x00\x00\x00\x02\x00", &parseOutput);
    assertEquals(false, parseOutput.isInvalid);
    assertEquals(FEET, parseOutput.chainCount.unit);
    assertEquals(107, parseOutput.chainCount.unitcount);

    parseCH1203Frame(0x6C2, 8, "\xC1\x18\x00\x00\x00\x00\x00\x00", &parseOutput);
    assertEquals(true, parseOutput.isInvalid);
    parseCH1203Frame(0x6C3, 8, "\xC1\x18\x00\x00\x00\x00\x00\x00", &parseOutput);
    assertEquals(true, parseOutput.isInvalid);
}
