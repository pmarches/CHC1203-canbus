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

int monitorCanSocket(char* interfaceName){
    int s, nbytes;
    struct sockaddr_can addr;
    struct ifreq ifr;
    struct can_frame frame;

    // Open socket
    if ((s = socket(PF_CAN, SOCK_RAW, CAN_RAW)) < 0) {
        perror("Error opening socket");
        return 1;
    }

    // Set up the can interface
    strcpy(ifr.ifr_name, interfaceName);
    ioctl(s, SIOCGIFINDEX, &ifr);
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    // Bind the socket to the can interface
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("Error binding socket to interface");
        close(s);
        return 1;
    }
#if 0
    // Set the baudrate to 62000 Kbps
    struct can_bittiming64 bt;
    bt.bitrate = 62000;
    bt.sample_point = 0.875; // You may need to adjust this value
    if (setsockopt(s, SOL_CAN_RAW, CAN_RAW_BITTIMING, &bt, sizeof(bt)) < 0) {
        perror("Error setting bitrate");
        close(s);
        return 1;
    }
#endif
    while (1) {
        // Read data in a loop
        nbytes = read(s, &frame, sizeof(struct can_frame));
        if (nbytes < 0) {
            perror("Error reading from socket");
            close(s);
            return 1;
        }

        // Process the received data
        printf("Received CAN frame: ID=%x, DLC=%d, Data=", frame.can_id, frame.can_dlc);
        for (int i = 0; i < frame.can_dlc; i++) {
            printf("%02X ", frame.data[i]);
        }
        printf("\n");
    }

    // Close the socket (unreachable in this example due to the infinite loop)
    close(s);
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
    
    monitorCanSocket("mvcan0");
}
