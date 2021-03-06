import numpy as np
import cv2


def createGaussianPyramid(im, sigma0=1, 
        k=np.sqrt(2), levels=[-1,0,1,2,3,4]):
    if len(im.shape)==3:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    if im.max()>10:
        im = np.float32(im)/255
    im_pyramid = []
    for i in levels:
        sigma_ = sigma0*k**i 
        im_pyramid.append(cv2.GaussianBlur(im, (0,0), sigma_))
    im_pyramid = np.stack(im_pyramid, axis=-1)
    return im_pyramid


def displayPyramid(im_pyramid):
    im_pyramid = np.split(im_pyramid, im_pyramid.shape[2], axis=2)
    im_pyramid = np.concatenate(im_pyramid, axis=1)
    im_pyramid = cv2.normalize(im_pyramid, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    cv2.imshow('Pyramid of image', im_pyramid)
    cv2.waitKey(0)  # press any key to exit
    cv2.destroyAllWindows()


def createDoGPyramid(gaussian_pyramid, levels=[-1,0,1,2,3,4]):
    '''
    Produces DoG Pyramid
    Inputs
    Gaussian Pyramid - A matrix of grayscale images of size
                        [imH, imW, len(levels)]
    levels      - the levels of the pyramid where the blur at each level is
                   outputs
    DoG Pyramid - size (imH, imW, len(levels) - 1) matrix of the DoG pyramid
                   created by differencing the Gaussian Pyramid input
    '''

    # compute DoG_pyramid here
    DoG_pyramid = gaussian_pyramid[:, :, 1:] - gaussian_pyramid[:, :, :-1]
    DoG_levels = levels[1:]
    return DoG_pyramid, DoG_levels


def computePrincipalCurvature(DoG_pyramid):
    '''
    Takes in DoGPyramid generated in createDoGPyramid and returns
    PrincipalCurvature,a matrix of the same size where each point contains the
    curvature ratio R for the corre-sponding point in the DoG pyramid
    
    INPUTS
        DoG Pyramid - size (imH, imW, len(levels) - 1) matrix of the DoG pyramid
    
    OUTPUTS
        principal_curvature - size (imH, imW, len(levels) - 1) matrix where each 
                          point contains the curvature ratio R for the 
                          corresponding point in the DoG pyramid
    '''
    # Compute principal curvature here
    principal_curvature = np.zeros(DoG_pyramid.shape)
    cnt = 0
    for i in range(DoG_pyramid.shape[-1]):
        gx = cv2.Sobel(DoG_pyramid[:, :, i], cv2.CV_64F, 1, 0, ksize=5)
        gy = cv2.Sobel(DoG_pyramid[:, :, i], cv2.CV_64F, 0, 1, ksize=5)
        gxx = cv2.Sobel(gx, cv2.CV_64F, 1, 0, ksize=5)
        gxy = cv2.Sobel(gx, cv2.CV_64F, 0, 1, ksize=5)
        gyx = cv2.Sobel(gy, cv2.CV_64F, 1, 0, ksize=5)
        gyy = cv2.Sobel(gy, cv2.CV_64F, 0, 1, ksize=5)
        for x in range(gx.shape[0]):
            for y in range(gx.shape[1]):
                H = np.matrix([[gxx[x, y], gxy[x, y]], [gyx[x, y], gyy[x, y]]])
                if np.linalg.det(H) < 1e-20: cnt += 1
                R = (np.trace(H))**2 / max(np.linalg.det(H), 1e-20)
                principal_curvature[x, y, i] = R
    # print(np.max(principal_curvature[:,:,0]))
    # print(np.min(principal_curvature[:,:,0]))
    print(cnt)
    return principal_curvature


def getLocalExtrema(DoG_pyramid, DoG_levels, principal_curvature,
        th_contrast=0.03, th_r=12):
    '''
    Returns local extrema points in both scale and space using the DoGPyramid

    INPUTS
        DoG_pyramid - size (imH, imW, len(levels) - 1) matrix of the DoG pyramid
        DoG_levels  - The levels of the pyramid where the blur at each level is
                      outputs
        principal_curvature - size (imH, imW, len(levels) - 1) matrix contains the
                      curvature ratio R
        th_contrast - remove any point that is a local extremum but does not have a
                      DoG response magnitude above this threshold
        th_r        - remove any edge-like points that have too large a principal
                      curvature ratio
     OUTPUTS
        locsDoG - N x 3 matrix where the DoG pyramid achieves a local extrema in both
               scale and space, and also satisfies the two thresholds.
    '''
    # Compute locsDoG here
    locsDoG = []
    imH = DoG_pyramid.shape[0]
    imW = DoG_pyramid.shape[1]
    l = DoG_pyramid.shape[2]
    index_d = np.array(np.where(abs(DoG_pyramid) > th_contrast)).transpose(1, 0)
    index_p = np.array(np.where(principal_curvature < th_r)).transpose(1, 0)
    # index_pp = np.array(np.where(principal_curvature < 50)).transpose(1, 0)
    candidates = np.array([x for x in set([tuple(x) for x in index_d]) &
                        set([tuple(x) for x in index_p])])
    print(index_p.shape, index_d.shape, candidates.shape)
    print(candidates)

    for x, y, c in candidates:
        # if c==0 or c==l-1 or x==0 or x==imH-1 or y==0 or y==imW: continue
        data = DoG_pyramid[max(0, x-1):min(imH-1, x+1), max(0, y-1):min(imW-1, y+1), c]
        if (np.sum(DoG_pyramid[x, y, c] > data) >= data.flatten().shape[0]-1
                    and (c == 0 or DoG_pyramid[x, y, c] > DoG_pyramid[x, y, c-1])\
                    and (c == l-1 or DoG_pyramid[x, y, c] > DoG_pyramid[x, y, c+1])) \
                or (np.sum(DoG_pyramid[x, y, c] < data) >= data.flatten().shape[0]-1
                    and (c == 0 or DoG_pyramid[x, y, c] < DoG_pyramid[x, y, c-1])\
                    and (c == l-1 or DoG_pyramid[x, y, c] < DoG_pyramid[x, y, c+1])):
            locsDoG.append([x, y, c])

    locsDoG = np.array(locsDoG)
    return locsDoG
    

def DoGdetector(im, sigma0=1, k=np.sqrt(2), levels=[-1,0,1,2,3,4], 
                th_contrast=0.03, th_r=12):
    '''
    Putting it all together

    Inputs          Description
    --------------------------------------------------------------------------
    im              Grayscale image with range [0,1].

    sigma0          Scale of the 0th image pyramid.

    k               Pyramid Factor.  Suggest sqrt(2).

    levels          Levels of pyramid to construct. Suggest -1:4.

    th_contrast     DoG contrast threshold.  Suggest 0.03.

    th_r            Principal Ratio threshold.  Suggest 12.

    Outputs         Description
    --------------------------------------------------------------------------

    locsDoG         N x 3 matrix where the DoG pyramid achieves a local extrema
                    in both scale and space, and satisfies the two thresholds.

    gauss_pyramid   A matrix of grayscale images of size (imH,imW,len(levels))
    '''
    ##########################
    # compupte gauss_pyramid, gauss_pyramid here
    gauss_pyramid = createGaussianPyramid(im, sigma0, k)
    DoG_pyr, DoG_levels = createDoGPyramid(gauss_pyramid, levels)
    pc_curvature = computePrincipalCurvature(DoG_pyr)
    locsDoG = getLocalExtrema(DoG_pyr, DoG_levels, pc_curvature, th_contrast, th_r)
    return locsDoG, gauss_pyramid


def display_keypoints(im, locsDoG):
    scale = 4
    im = cv2.resize(im, (im.shape[1]*scale, im.shape[0]*scale))
    # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    for loc in locsDoG:
        cv2.circle(im, (loc[1]*scale, loc[0]*scale), 3, (0, 255, 0), -1)
    cv2.imshow('image', im)
    cv2.waitKey(0)  # press any key to exit
    cv2.destroyAllWindows()


if __name__ == '__main__':
    # test gaussian pyramid
    levels = [-1, 0, 1, 2, 3, 4]
    im = cv2.imread('../data/model_chickenbroth.jpg')
    # im_pyr = createGaussianPyramid(im)
    # displayPyramid(im_pyr)

    # # test DoG pyramid
    # DoG_pyr, DoG_levels = createDoGPyramid(im_pyr, levels)
    # # displayPyramid(DoG_pyr)
    #
    # # test compute principal curvature
    # pc_curvature = computePrincipalCurvature(DoG_pyr)
    # # displayPyramid(pc_curvature)
    #
    # # test get local extrema
    # th_contrast = 0.03
    # th_r = 12
    # locsDoG = getLocalExtrema(DoG_pyr, DoG_levels, pc_curvature, th_contrast, th_r)

    # test DoG detector
    locsDoG, gaussian_pyramid = DoGdetector(im)
    print(locsDoG.shape)
    display_keypoints(im, locsDoG)

